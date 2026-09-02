from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from backend.auth.dependencies import get_current_patient, get_db
from backend.models.data_models import Appointment, AppointmentStatus, Patient
from backend.session.store import get_intent_greeting, store as session_store

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class AssistantActionResponse(BaseModel):
    """Information the client needs to open the appointment assistant."""

    action: Literal["cancel", "reschedule", "followup"]
    intent: str
    session_id: str
    message: str
    assistant_reply_url: str = "/chat/session/reply"
    appointment: dict


_ACTION_INTENTS = {
    "cancel": "CANCEL_APPOINTMENT",
    "reschedule": "RESCHEDULE_APPOINTMENT",
    "followup": "FOLLOWUP_APPOINTMENT",
}


def _appointment_context(appointment: Appointment) -> dict:
    """Return only the appointment details useful to the assistant UI."""
    return {
        "appointment_id": appointment.id,
        "datetime": appointment.appointment_datetime.isoformat(),
        "status": appointment.status.value,
        "problem": appointment.patient_problem,
        "doctor_name": appointment.doctor.name if appointment.doctor else "Unknown",
        "department_name": appointment.department.name if appointment.department else "Unknown",
    }


def _get_patient_appointment_or_404(
    appointment_id: int, patient_id: int, db: Session
) -> Appointment:
    """Fetch an appointment only when it belongs to the logged-in patient."""
    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.department))
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id,
        )
        .one_or_none()
    )
    if appointment is None:
        # Do not reveal whether another patient's appointment ID exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    return appointment


def _start_assistant_action(
    action: Literal["cancel", "reschedule", "followup"],
    appointment_id: int,
    patient: Patient,
    db: Session,
) -> AssistantActionResponse:
    """Start a guided assistant session with a verified appointment ID."""
    appointment = _get_patient_appointment_or_404(appointment_id, patient.id, db)

    # Cancellation and rescheduling tools only accept currently booked visits.
    if action in {"cancel", "reschedule"} and appointment.status != AppointmentStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Only BOOKED appointments can be {action}d. "
                f"This appointment is {appointment.status.value}."
            ),
        )
    if action == "followup" and appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A follow-up cannot be started from a cancelled appointment.",
        )

    intent = _ACTION_INTENTS[action]
    session_id = session_store.register(
        patient_id=patient.id,
        intent=intent,
        appointment_id=appointment.id,
    )
    return AssistantActionResponse(
        action=action,
        intent=intent,
        session_id=session_id,
        message=get_intent_greeting(intent, appointment_id=appointment.id),
        appointment=_appointment_context(appointment),
    )

@router.get("/history")
def get_appointment_history(
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)]
):
    """Fetch the appointment history for the authenticated patient."""
    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.department))
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )
    
    results = []
    for appt in appointments:
        item = _appointment_context(appt)
        item["actions"] = {
            "cancel": f"/appointments/{appt.id}/cancel",
            "reschedule": f"/appointments/{appt.id}/reschedule",
            "followup": f"/appointments/{appt.id}/followup",
        }
        item["can_cancel"] = appt.status == AppointmentStatus.BOOKED
        item["can_reschedule"] = appt.status == AppointmentStatus.BOOKED
        item["can_followup"] = appt.status != AppointmentStatus.CANCELLED
        results.append(item)
    return {"history": results}


@router.post("/{appointment_id}/cancel", response_model=AssistantActionResponse)
def start_cancel_assistant(
    appointment_id: int,
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> AssistantActionResponse:
    """Open the assistant with this appointment pre-selected for cancellation."""
    return _start_assistant_action("cancel", appointment_id, patient, db)


@router.post("/{appointment_id}/reschedule", response_model=AssistantActionResponse)
def start_reschedule_assistant(
    appointment_id: int,
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> AssistantActionResponse:
    """Open the assistant with this appointment pre-selected for rescheduling."""
    return _start_assistant_action("reschedule", appointment_id, patient, db)


@router.post("/{appointment_id}/followup", response_model=AssistantActionResponse)
def start_followup_assistant(
    appointment_id: int,
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> AssistantActionResponse:
    """Open the assistant with this appointment pre-selected for follow-up."""
    return _start_assistant_action("followup", appointment_id, patient, db)

