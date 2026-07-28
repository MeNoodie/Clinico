"""Appointment database tools used by the Appointment Agent.

Agents should use the functions in this module instead of querying ORM models
directly.  Each public function owns its database session so it is safe to use
from synchronous agent tools.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TypeAlias

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.models.data_models import (
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    DoctorWorkingDay,
    Patient,
)


SLOT_INTERVAL = timedelta(minutes=30)
MAX_SUGGESTIONS = 5
MAX_SEARCH_DAYS = 60

BookingResult: TypeAlias = dict[str, object]
AppointmentResult: TypeAlias = dict[str, object]


def _validate_datetime(appointment_datetime: datetime) -> datetime:
    """Validate and normalize a requested appointment datetime.

    SQLite stores naive datetimes in this application.  Timezone-aware values
    are rejected so comparisons cannot silently use a different local time.
    """
    if not isinstance(appointment_datetime, datetime):
        raise ValueError("appointment_datetime must be a datetime instance")
    if appointment_datetime.tzinfo is not None and appointment_datetime.utcoffset() is not None:
        raise ValueError("appointment_datetime must be timezone-naive")
    if appointment_datetime.second or appointment_datetime.microsecond:
        raise ValueError("appointment_datetime must be precise to the minute")
    return appointment_datetime


def _get_department(session: Session, department_name: str) -> Department:
    """Fetch a department by name or raise a clear validation error."""
    if not isinstance(department_name, str) or not department_name.strip():
        raise ValueError("department_name must be a non-empty string")

    department = session.scalar(
        select(Department).where(Department.name.ilike(department_name.strip()))
    )
    if department is None:
        raise ValueError(f"Department '{department_name}' does not exist")
    return department


def _get_doctors(session: Session, department_id: int) -> list[Doctor]:
    """Fetch doctors for an existing department, in a stable order."""
    if not isinstance(department_id, int) or isinstance(department_id, bool):
        raise ValueError("department_id must be an integer")
    return list(
        session.scalars(
            select(Doctor).where(Doctor.department_id == department_id).order_by(Doctor.id)
        ).all()
    )


def _is_doctor_working(session: Session, doctor_id: int, appointment_datetime: datetime) -> bool:
    """Return whether a doctor works on the requested weekday."""
    weekday = appointment_datetime.strftime("%A")
    return (
        session.scalar(
            select(DoctorWorkingDay.id).where(
                DoctorWorkingDay.doctor_id == doctor_id,
                DoctorWorkingDay.day_of_week == weekday,
            )
        )
        is not None
    )


def _is_slot_available(session: Session, doctor_id: int, appointment_datetime: datetime) -> bool:
    """Return whether a doctor has no BOOKED appointment at the requested time."""
    booked_appointment = session.scalar(
        select(Appointment.id).where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_datetime == appointment_datetime,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    )
    return booked_appointment is None


def _get_patient(session: Session, patient_id: int) -> Patient:
    """Fetch a patient to prevent orphaned bookings when SQLite FKs are disabled."""
    if not isinstance(patient_id, int) or isinstance(patient_id, bool):
        raise ValueError("patient_id must be an integer")
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise ValueError(f"Patient with id {patient_id} does not exist")
    return patient


def _get_patient_appointment(
    session: Session, appointment_id: int, patient_id: int
) -> Appointment:
    """Fetch an appointment only when it belongs to the requesting patient."""
    if not isinstance(appointment_id, int) or isinstance(appointment_id, bool):
        raise ValueError("appointment_id must be an integer")
    _get_patient(session, patient_id)
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise ValueError(f"Appointment with id {appointment_id} does not exist")
    if appointment.patient_id != patient_id:
        raise ValueError("Appointment does not belong to patient_id")
    return appointment


def _validate_booked_appointment(appointment: Appointment) -> None:
    """Ensure an appointment can still be changed by the patient."""
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError(
            f"Only BOOKED appointments can be changed; this appointment is {appointment.status.value}"
        )


def get_department_by_name(department_name: str) -> Department:
    """Return the department matching ``department_name``.

    Raises:
        ValueError: If the name is invalid or no matching department exists.
    """
    with SessionLocal() as session:
        return _get_department(session, department_name)


def get_doctors_by_department(department_id: int) -> list[Doctor]:
    """Return all doctors belonging to ``department_id``."""
    with SessionLocal() as session:
        return _get_doctors(session, department_id)


def is_doctor_working(doctor_id: int, appointment_datetime: datetime) -> bool:
    """Return whether the doctor is scheduled to work that weekday."""
    scheduled_at = _validate_datetime(appointment_datetime)
    with SessionLocal() as session:
        return _is_doctor_working(session, doctor_id, scheduled_at)


def is_within_working_hours(doctor: Doctor, appointment_datetime: datetime) -> bool:
    """Return whether the requested time falls within the doctor's working hours.

    The end time is exclusive: a doctor working until 17:00 is not available at
    exactly 17:00.
    """
    scheduled_at = _validate_datetime(appointment_datetime)
    if not isinstance(doctor, Doctor):
        raise ValueError("doctor must be a Doctor instance")
    requested_time = scheduled_at.time()
    return doctor.work_start_time <= requested_time < doctor.work_end_time


def is_slot_available(doctor_id: int, appointment_datetime: datetime) -> bool:
    """Return ``True`` when no BOOKED appointment occupies this doctor/time slot."""
    scheduled_at = _validate_datetime(appointment_datetime)
    with SessionLocal() as session:
        return _is_slot_available(session, doctor_id, scheduled_at)


def book_appointment(
    patient_id: int,
    doctor_id: int,
    department_id: int,
    appointment_datetime: datetime,
    patient_problem: str,
) -> Appointment:
    """Create and commit a BOOKED appointment after validating its references.

    Raises:
        ValueError: For invalid inputs, references, or an occupied doctor slot.
        RuntimeError: If the database cannot persist the appointment.
    """
    scheduled_at = _validate_datetime(appointment_datetime)
    if not isinstance(doctor_id, int) or isinstance(doctor_id, bool):
        raise ValueError("doctor_id must be an integer")
    if not isinstance(department_id, int) or isinstance(department_id, bool):
        raise ValueError("department_id must be an integer")
    if not isinstance(patient_problem, str) or not patient_problem.strip():
        raise ValueError("patient_problem must be a non-empty string")

    with SessionLocal() as session:
        _get_patient(session, patient_id)
        doctor = session.get(Doctor, doctor_id)
        if doctor is None:
            raise ValueError(f"Doctor with id {doctor_id} does not exist")
        if doctor.department_id != department_id:
            raise ValueError("doctor_id does not belong to department_id")
        if session.get(Department, department_id) is None:
            raise ValueError(f"Department with id {department_id} does not exist")
        if not _is_doctor_working(session, doctor_id, scheduled_at):
            raise ValueError("Doctor is not working on the requested day")
        if not is_within_working_hours(doctor, scheduled_at):
            raise ValueError("Requested time is outside the doctor's working hours")
        if not _is_slot_available(session, doctor_id, scheduled_at):
            raise ValueError("Requested appointment slot is no longer available")

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            appointment_datetime=scheduled_at,
            patient_problem=patient_problem.strip(),
            status=AppointmentStatus.BOOKED,
        )
        session.add(appointment)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Unable to book appointment; conflicting appointment data") from exc
        except SQLAlchemyError as exc:
            session.rollback()
            raise RuntimeError("Unable to save appointment") from exc
        session.refresh(appointment)
        return appointment


def _candidate_times(doctor: Doctor, date_value: datetime) -> list[datetime]:
    """Generate 30-minute appointment start times within a doctor's shift."""
    candidate = datetime.combine(date_value.date(), doctor.work_start_time)
    end = datetime.combine(date_value.date(), doctor.work_end_time)
    slots: list[datetime] = []
    while candidate < end:
        slots.append(candidate)
        candidate += SLOT_INTERVAL
    return slots


def suggest_alternative_slots(department_id: int, appointment_datetime: datetime) -> list[str]:
    """Return up to five nearest available 30-minute slots for the department.

    Search begins on the requested date, then moves forward to the next working
    days, checking all doctors in the same department.
    """
    scheduled_at = _validate_datetime(appointment_datetime)
    with SessionLocal() as session:
        doctors = _get_doctors(session, department_id)
        suggestions: list[datetime] = []
        seen: set[datetime] = set()

        for day_offset in range(MAX_SEARCH_DAYS + 1):
            search_date = scheduled_at + timedelta(days=day_offset)
            for doctor in doctors:
                if not _is_doctor_working(session, doctor.id, search_date):
                    continue
                for candidate in _candidate_times(doctor, search_date):
                    if day_offset == 0 and candidate < scheduled_at:
                        continue
                    if candidate in seen or not _is_slot_available(session, doctor.id, candidate):
                        continue
                    seen.add(candidate)
                    suggestions.append(candidate)

            if suggestions:
                suggestions.sort()
                if len(suggestions) >= MAX_SUGGESTIONS:
                    break

        return [
            f"{slot.day} {slot.strftime('%B')} {slot.strftime('%I').lstrip('0')}:{slot:%M} {slot:%p}"
            for slot in suggestions[:MAX_SUGGESTIONS]
        ]


def process_booking_request(
    patient_id: int,
    department_name: str,
    appointment_datetime: datetime,
    patient_problem: str,
) -> BookingResult:
    """Book the first eligible department doctor or suggest nearby open slots."""
    scheduled_at = _validate_datetime(appointment_datetime)
    # Validate this before availability checks so an invalid patient cannot be
    # masked by a suggestion response when every doctor is unavailable.
    with SessionLocal() as session:
        _get_patient(session, patient_id)
    department = get_department_by_name(department_name)
    doctors = get_doctors_by_department(department.id)

    for doctor in doctors:
        if not is_doctor_working(doctor.id, scheduled_at):
            continue
        if not is_within_working_hours(doctor, scheduled_at):
            continue
        if not is_slot_available(doctor.id, scheduled_at):
            continue

        try:
            appointment = book_appointment(
                patient_id=patient_id,
                doctor_id=doctor.id,
                department_id=department.id,
                appointment_datetime=scheduled_at,
                patient_problem=patient_problem,
            )
        except ValueError as exc:
            # A concurrent booking can claim the slot after the availability check.
            if str(exc) == "Requested appointment slot is no longer available":
                continue
            raise
        return {
            "status": "BOOKED",
            "appointment_id": appointment.id,
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "doctor_id": appointment.doctor_id,
            "doctor_name": doctor.name,
            "department": department.name,
            "patient_problem": appointment.patient_problem,
        }

    return {
        "status": "SUGGEST_SLOT",
        "available_slots": suggest_alternative_slots(department.id, scheduled_at),
    }
