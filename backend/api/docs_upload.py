"""Patient-scoped medical document upload and retrieval endpoints."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_patient, get_db
from backend.models.data_models import MedicalDocument, Patient

router = APIRouter(prefix="/documents", tags=["Medical documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024
STORAGE_ROOT = Path(
    os.getenv(
        "MEDICAL_DOCUMENTS_DIR",
        (Path(__file__).resolve().parents[2] / "uploads" / "medical_documents").as_posix(),
    )
).resolve()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
_SIGNATURES = {
    ".pdf": ("application/pdf", lambda data: data.startswith(b"%PDF-")),
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
}
_MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def _safe_original_filename(filename: str | None) -> str:
    raw_name = (filename or "medical-report").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", raw_name).strip(" .")
    return (cleaned or "medical-report")[:255]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    """Store a PDF/JPG/PNG report and associate its metadata with the logged-in patient."""
    filename = _safe_original_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported file types are PDF, JPG, JPEG, and PNG.",
        )

    content = file.file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Files must be 10 MB or smaller.")

    file_type, signature_matches = _SIGNATURES[suffix]
    if not signature_matches(content):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file contents do not match a supported PDF or image format.",
        )

    document = MedicalDocument(
        patient_id=patient.id,
        filename=filename,
        file_type=file_type,
    )
    stored_path: Path | None = None
    try:
        db.add(document)
        db.flush()
        patient_directory = (STORAGE_ROOT / str(patient.id)).resolve()
        if STORAGE_ROOT not in patient_directory.parents:
            raise RuntimeError("Invalid patient storage path")
        patient_directory.mkdir(parents=True, exist_ok=True)
        stored_path = patient_directory / f"{document.id}{_MIME_EXTENSIONS[file_type]}"
        stored_path.write_bytes(content)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        raise

    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "uploaded_at": document.uploaded_at.isoformat(),
    }


@router.get("/recent")
def get_recent_documents(
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    """List only the authenticated patient's most recently uploaded reports."""
    documents = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.patient_id == patient.id)
        .order_by(MedicalDocument.uploaded_at.desc(), MedicalDocument.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "file_type": document.file_type,
                "uploaded_at": document.uploaded_at.isoformat(),
                "download_url": f"/documents/{document.id}/download",
            }
            for document in documents
        ]
    }


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Download a report only when it belongs to the authenticated patient."""
    document = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.id == document_id,
            MedicalDocument.patient_id == patient.id,
        )
        .one_or_none()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    extension = _MIME_EXTENSIONS.get(document.file_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")
    patient_directory = (STORAGE_ROOT / str(patient.id)).resolve()
    if STORAGE_ROOT not in patient_directory.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")
    stored_path = patient_directory / f"{document.id}{extension}"
    if not stored_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")

    return FileResponse(
        path=stored_path,
        media_type=document.file_type,
        filename=document.filename,
    )


@router.get("/{document_id}/view")
def view_document(
    document_id: int,
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Display an inline preview for a document owned by the authenticated patient."""
    document = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.id == document_id,
            MedicalDocument.patient_id == patient.id,
        )
        .one_or_none()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    extension = _MIME_EXTENSIONS.get(document.file_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")
    patient_directory = (STORAGE_ROOT / str(patient.id)).resolve()
    if STORAGE_ROOT not in patient_directory.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")
    stored_path = patient_directory / f"{document.id}{extension}"
    if not stored_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")

    return FileResponse(
        path=stored_path,
        media_type=document.file_type,
        filename=document.filename,
        content_disposition_type="inline",
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_document(
    document_id: int,
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Delete a document and its stored file, limited to its owning patient."""
    document = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.id == document_id,
            MedicalDocument.patient_id == patient.id,
        )
        .one_or_none()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    extension = _MIME_EXTENSIONS.get(document.file_type)
    if extension:
        patient_directory = (STORAGE_ROOT / str(patient.id)).resolve()
        if STORAGE_ROOT not in patient_directory.parents:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")
        (patient_directory / f"{document.id}{extension}").unlink(missing_ok=True)

    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
