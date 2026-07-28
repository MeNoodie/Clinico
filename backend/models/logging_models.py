"""Pydantic schemas for logging and document metadata."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from backend.models.data_models import ActionType

class AuditLogCreate(BaseModel):
    patient_id: int
    action_type: ActionType
    details: Optional[str] = None


class MedicalDocumentCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    filename: str
    file_type: str
