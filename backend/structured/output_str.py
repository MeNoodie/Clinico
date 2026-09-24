from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal, Optional, Union
  
 
class CoordinatorOutput(BaseModel):
    normalized_query: str

    intent: str = Field(
        description=(
            "BOOK_APPOINTMENT, RESCHEDULE_APPOINTMENT, "
            "CANCEL_APPOINTMENT, FOLLOWUP_APPOINTMENT, OTHER"
        )
    )

    problem: Optional[str] = None

    @field_validator("problem", mode="before")
    @classmethod
    def clean_empty_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip().lower() in {
            "none", "null", "none.", "n/a", ""
        }:
            return None
        return v

class SafetyOutput(BaseModel):
    """Structured result returned by the dedicated Safety Agent."""
    status: Literal["NORMAL", "EMERGENCY", "ERROR"]
    reason: str = Field(min_length=1, max_length=500)


class RouterOutput(BaseModel):
    """Structured result returned by the Routing Agent."""

    department: Optional[str] = Field(
        default=None,
        description="the hospital department to route to (e.g. Cardiology, Dentistry, Dermatology, ENT, Neurology, Orthopedics, General Medicine)"
    )
    appointment_datetime: Optional[str] = Field(
        default=None,
        description="date/time in ISO-8601 format (e.g. '2026-07-28T10:00:00')"
    )



