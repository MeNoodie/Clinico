"""Appointment cancellation tools used by the Appointment Agent.

Agents should use the functions in this module instead of querying ORM models
directly. Each public function owns its database session so it is safe to use
from synchronous agent tools.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.tools.appointment_tools import (
    _get_patient,
    _get_patient_appointment,
    _validate_booked_appointment,
)
from backend.models.data_models import AppointmentStatus, AuditLog, ActionType


def _process_cancel_request(
    session: Session, appointment_id: int, patient_id: int
) -> dict:
    """Cancel an appointment for a patient.

    Args:
        session: Database session.
        appointment_id: ID of the appointment to cancel.
        patient_id: ID of the patient (for ownership verification).

    Returns:
        Dictionary with status and the cancelled appointment.
    """
    appointment = _get_patient_appointment(session, appointment_id, patient_id)
    _validate_booked_appointment(appointment)
    appointment.status = AppointmentStatus.CANCELLED
    
    audit_log = AuditLog(
        patient_id=patient_id,
        action_type=ActionType.CANCEL,
        details=f"Cancelled appointment {appointment.id}"
    )
    session.add(audit_log)

    session.commit()
    return {
        "status": "CANCELLED",
        "appointment_id": appointment.id,
        "appointment_datetime": appointment.appointment_datetime.isoformat(),
        "patient_problem": appointment.patient_problem,
        "doctor_id": appointment.doctor_id,
        "department_id": appointment.department_id,
    }


def process_cancel_request(appointment_id: int, patient_id: int) -> dict:
    """Process a cancellation request for an appointment.

    Args:
        appointment_id: ID of the appointment to cancel.
        patient_id: ID of the patient (for ownership verification).

    Returns:
        Dictionary with status and the cancelled appointment.
    """
    with SessionLocal() as session:
        return _process_cancel_request(session, appointment_id, patient_id)