"""Authenticated API for the appointment workflow."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.agents.graph import run_booking_workflow
from backend.auth.dependencies import get_current_patient
from backend.models.data_models import Patient


router = APIRouter(prefix="/chat", tags=["Appointments"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2_000)
    problem: str | None = Field(default=None, max_length=2_000)
    department: str | None = Field(default=None, max_length=100)
    appointment_datetime: str | None = Field(
        default=None, description="Preferred local ISO-8601 datetime, for example 2026-07-27T10:30:00"
    )


class TestChatRequest(BaseModel):
    """Swagger-friendly request that accepts patient_id directly (no JWT)."""
    patient_id: int = Field(description="ID of a seeded patient (1-6)")
    message: str = Field(min_length=2, max_length=2_000)
    problem: str | None = Field(default=None, max_length=2_000)
    department: str | None = Field(default=None, max_length=100)
    appointment_datetime: str | None = Field(
        default=None, description="Preferred local ISO-8601 datetime, for example 2026-07-28T10:00:00"
    )
    appointment_id: int | None = Field(
        default=None, description="Existing appointment ID (for cancel/reschedule/followup)"
    )


class ChatResponse(BaseModel):
    message: str
    department: str | None = None
    intent: str
    safety_status: str
    appointment_id: int | None = None
    booked_datetime: str | None = None
    alternative_slots: list[str] = Field(default_factory=list)


@router.post("/appointments", response_model=ChatResponse)
def create_appointment(
    payload: ChatRequest,
    patient: Annotated[Patient, Depends(get_current_patient)],
) -> ChatResponse:
    state = run_booking_workflow({
        "query": payload.message, "patient_id": patient.id, "problem": payload.problem or payload.message,
        "department": payload.department, "appointment_datetime": payload.appointment_datetime,
    })
    return ChatResponse(
        message=state["final_message"], department=state.get("department"),
        intent=state["intent"], safety_status=state["safety_status"], appointment_id=state.get("appointment_id"),
        booked_datetime=state.get("booked_datetime"), alternative_slots=state.get("alt_slots", []),
    )


@router.post("/test", response_model=ChatResponse, summary="Test workflow without JWT")
def test_appointment(payload: TestChatRequest) -> ChatResponse:
    """Unauthenticated endpoint for Swagger testing. Uses patient_id directly."""
    initial = {
        "query": payload.message,
        "patient_id": payload.patient_id,
        "problem": payload.problem or payload.message,
        "department": payload.department,
        "appointment_datetime": payload.appointment_datetime,
    }
    if payload.appointment_id is not None:
        initial["appointment_id"] = payload.appointment_id
    state = run_booking_workflow(initial)
    return ChatResponse(
        message=state.get("final_message", ""),
        department=state.get("department"),
        intent=state.get("intent", "UNKNOWN"),
        safety_status=state.get("safety_status", "UNKNOWN"),
        appointment_id=state.get("appointment_id"),
        booked_datetime=state.get("booked_datetime"),
        alternative_slots=state.get("alt_slots", []),
    )

