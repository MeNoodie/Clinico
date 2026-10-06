from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.auth.dependencies import get_current_patient, get_db
from backend.models.data_models import MedicalDocument, Patient, PatientConversation

router = APIRouter(prefix="/dashboard", tags=["Patient dashboard"])


@router.get("/stats")
def patient_dashboard_stats(
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    """Return totals scoped to the authenticated patient."""
    return {
        "document_count": db.query(MedicalDocument).filter(
            MedicalDocument.patient_id == patient.id
        ).count(),
        "conversation_count": db.query(PatientConversation).filter(
            PatientConversation.patient_id == patient.id
        ).count(),
    }
    



