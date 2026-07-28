from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional
  
 
class CoordinatorOutput(BaseModel):
    """Structured output from coordinator node"""
    
    intent: str = Field(
        description="one of: BOOK_APPOINTMENT, RESCHEDULE_APPOINTMENT, CANCEL_APPOINTMENT, FOLLOWUP_APPOINTMENT, OTHER"
    )
    problem: Optional[str] = Field(
        default=None,
        description="medical problem or symptom mentioned"
    )
    department: Optional[str] = Field(
        default=None,
        description="department if patient mentioned it explicitly (e.g. Cardiology). null if only symptom mentioned"
    )
    appointment_datetime: Optional[str] = Field(
        default=None,
        description="date/time in ISO-8601 format (e.g. '2026-07-28T10:00:00')"
    )


class SafetyOutput(BaseModel):
    """Structured result returned by the dedicated Safety Agent."""

    status: Literal["NORMAL", "EMERGENCY"]
    reason: str = Field(min_length=1, max_length=500)


class RouterOutput(BaseModel):
    """Structured result returned by the Routing Agent."""

    department: Optional[str] = Field(
        default=None,
        description="the hospital department to route to (e.g. Cardiology, Dentistry, Dermatology, ENT, Neurology, Orthopedics, General Medicine)"
    )
