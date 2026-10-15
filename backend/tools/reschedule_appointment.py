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
    AuditLog,
    ActionType,
)
from backend.tools.appointment_tools import (
    _validate_datetime,
    _get_patient_appointment,
    _validate_booked_appointment,
    _is_doctor_working,
    _is_slot_available,
    suggest_alternative_slots,
    is_within_working_hours,
    _get_doctors,
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

    # Keep the current doctor when possible, then check the other doctors in
    # the same department. A doctor being off at this time does not mean the
    # department has no appointment available.
    doctors = _get_doctors(session, appointment.department_id)
    doctors.sort(key=lambda item: item.id != appointment.doctor_id)
    selected_doctor = None
    for doctor in doctors:
        if not _is_doctor_working(session, doctor.id, validated_dt):
            continue
        if not is_within_working_hours(doctor, validated_dt):
            continue
        if not _is_slot_available(session, doctor.id, validated_dt):
            continue
        selected_doctor = doctor
        break

    if selected_doctor is None:
        # This helper checks all doctors in the department and searches the
        # requested date first, then later dates.
        available_slots = suggest_alternative_slots(
            appointment.department_id, validated_dt
        )
        return {
            "status": "SUGGEST_SLOT",
            "available_slots": available_slots,
        }

    # Update appointment
    appointment.doctor_id = selected_doctor.id
    appointment.appointment_datetime = validated_dt
    if patient_problem is not None:
        appointment.patient_problem = patient_problem
        
    audit_log = AuditLog(
        patient_id=patient_id,
        action_type=ActionType.RESCHEDULE,
        details=(
            f"Rescheduled appointment {appointment.id} with doctor "
            f"{selected_doctor.id} to {validated_dt.isoformat()}"
        )
    )
    session.add(audit_log)
    
    session.commit()
    return {
        "status": "RESCHEDULED",
        "appointment_id": appointment.id,
        "appointment_datetime": appointment.appointment_datetime.isoformat(),
        "patient_problem": appointment.patient_problem,
        "doctor_id": appointment.doctor_id,
        "doctor_name": selected_doctor.name,
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
