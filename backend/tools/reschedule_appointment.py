"""Appointment rescheduling tools used by the Appointment Agent.

Agents should use the functions in this module instead of querying ORM models
directly. Each public function owns its database session so it is safe to use
from synchronous agent tools.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.models.data_models import (
    Appointment,
    AppointmentStatus,
    Doctor,
)
from backend.tools.appointment_tools import (
    _validate_datetime,
    _get_patient_appointment,
    _validate_booked_appointment,
    _is_doctor_working,
    _is_slot_available,
    suggest_alternative_slots,
    is_within_working_hours,
    get_doctors_by_department,
)


def _process_reschedule_request(
    session: Session,
    appointment_id: int,
    patient_id: int,
    appointment_datetime: datetime,
    patient_problem: str | None,
) -> dict[str, Any]:
    """Reschedule an appointment for a patient.

    Args:
        session: Database session.
        appointment_id: ID of the appointment to reschedule.
        patient_id: ID of the patient (for ownership verification).
        appointment_datetime: New requested appointment datetime.
        patient_problem: Optional updated problem description.

    Returns:
        Dictionary with status and either the rescheduled appointment or suggested slots.
    """
    appointment = _get_patient_appointment(session, appointment_id, patient_id)
    _validate_booked_appointment(appointment)
    validated_dt = _validate_datetime(appointment_datetime)

    # Get doctor and check if they work at the new time
    doctor_id = appointment.doctor_id
    doctor = session.get(Doctor, doctor_id)
    if doctor is None:
        raise ValueError(f"Doctor with id {doctor_id} does not exist")

    if not _is_doctor_working(session, doctor_id, validated_dt):
        raise ValueError("Doctor is not working at the requested time")

    # Check if within working hours
    if not is_within_working_hours(doctor, validated_dt):
        raise ValueError("Requested time is outside the doctor's working hours")

    # Check if slot is available
    if not _is_slot_available(session, doctor_id, validated_dt):
        # Suggest alternative slots for the same doctor's department
        department_id = appointment.department_id
        available_slots = suggest_alternative_slots(department_id, validated_dt)
        return {
            "status": "SUGGEST_SLOT",
            "available_slots": available_slots,
        }

    # Update appointment
    appointment.appointment_datetime = validated_dt
    if patient_problem is not None:
        appointment.patient_problem = patient_problem
    session.commit()
    return {
        "status": "RESCHEDULED",
        "appointment_id": appointment.id,
        "appointment_datetime": appointment.appointment_datetime.isoformat(),
        "patient_problem": appointment.patient_problem,
        "doctor_id": appointment.doctor_id,
        "department_id": appointment.department_id,
    }


def process_reschedule_request(
    appointment_id: int,
    patient_id: int,
    appointment_datetime: datetime,
    patient_problem: str | None = None,
) -> dict[str, Any]:
    """Process a reschedule request for an appointment.

    Args:
        appointment_id: ID of the appointment to reschedule.
        patient_id: ID of the patient (for ownership verification).
        appointment_datetime: New requested appointment datetime.
        patient_problem: Optional updated problem description.

    Returns:
        Dictionary with status and either the rescheduled appointment or suggested slots.
    """
    with SessionLocal() as session:
        return _process_reschedule_request(
            session, appointment_id, patient_id, appointment_datetime, patient_problem
        )