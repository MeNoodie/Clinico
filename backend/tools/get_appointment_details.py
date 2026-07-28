"""Appointment detail retrieval tools used by the Appointment Agent.

Agents should use the functions in this module instead of querying ORM models
directly. Each public function owns its database session so it is safe to use
from synchronous agent tools.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.models.data_models import Appointment, AppointmentStatus, Department, Doctor, Patient
from backend.tools.appointment_tools import (
    _get_patient,
    _get_patient_appointment,
    _validate_booked_appointment,
)


def _get_appointment_details(
    session: Session, appointment_id: int, patient_id: int
) -> dict[str, Any]:
    """Get detailed information about an appointment for a patient.

    Args:
        session: Database session.
        appointment_id: ID of the appointment.
        patient_id: ID of the patient (for ownership verification).

    Returns:
        Dictionary containing appointment details.
    """
    appointment = _get_patient_appointment(session, appointment_id, patient_id)

    # Get related objects
    patient = session.get(Patient, appointment.patient_id)
    doctor = session.get(Doctor, appointment.doctor_id)
    department = session.get(Department, appointment.department_id) if doctor else None

    # Format the appointment datetime for display
    appointment_dt = appointment.appointment_datetime
    formatted_time = appointment_dt.strftime("%A, %B %d, %Y at %I:%M %p")

    return {
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": patient.name if patient else "Unknown",
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor.name if doctor else "Unknown",
        "department_id": appointment.department_id,
        "department_name": department.name if department else "Unknown",
        "appointment_datetime": appointment_dt.isoformat(),
        "formatted_time": formatted_time,
        "patient_problem": appointment.patient_problem,
        "status": appointment.status.value,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
    }


def get_appointment_details(appointment_id: int, patient_id: int) -> dict[str, Any]:
    """Get detailed information about an appointment for a patient.

    Args:
        appointment_id: ID of the appointment.
        patient_id: ID of the patient (for ownership verification).

    Returns:
        Dictionary containing appointment details.
    """
    with SessionLocal() as session:
        return _get_appointment_details(session, appointment_id, patient_id)