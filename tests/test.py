from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

# Ensure project root is in sys.path when running scripts directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.db import SessionLocal
from backend.models.data_models import Patient, User
from backend.tools.appointment_tools import process_booking_request


def _get_or_create_patient() -> int:
    with SessionLocal() as session:
        patient = session.scalars(select(Patient)).first()
        if patient:
            return patient.id

        unique = uuid4().hex[:8]
        user = User(
            name="Test Patient",
            email=f"patient_{unique}@example.com",
            phone=f"+91-{uuid4().int % 10**10:010d}",
            hashed_password="hashed_placeholder_pw",
        )
        session.add(user)
        session.flush()

        new_patient = Patient(
            user_id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
        )
        session.add(new_patient)
        session.commit()
        return new_patient.id


def test_booking_request():
    patient_id = _get_or_create_patient()

    # Pick a future weekday (Monday-Friday) at 11:00 AM
    target_date = datetime.now() + timedelta(days=5)
    while target_date.weekday() >= 5:  # Skip Saturday/Sunday
        target_date += timedelta(days=1)
    appointment_dt = target_date.replace(hour=11, minute=0, second=0, microsecond=0)

    booking_request = {
        "patient_id": patient_id,
        "department_name": "cardiology",
        "appointment_datetime": appointment_dt,
        "patient_problem": "chest pain",
    }

    user_query = (
        f"Book {booking_request['department_name'].title()} appointment for '{booking_request['patient_problem']}' "
        f"on {appointment_dt.strftime('%A, %d %B %Y at %I:%M %p')} (Patient ID #{patient_id})"
    )

    print("\n" + "=" * 50)
    print("  TEST: Process Appointment Booking Request")
    print("=" * 50)
    print(f"  [USER QUERY]      : {user_query}")

    result = process_booking_request(**booking_request)

    assert result is not None
    assert "status" in result
    assert result["status"] in ("BOOKED", "SUGGEST_SLOT")

    if result["status"] == "BOOKED":
        assert result["appointment_id"] is not None
        assert result["doctor_name"] is not None
        assistant_reply = (
            f"Your appointment is confirmed! Appointment ID #{result['appointment_id']} "
            f"with {result['doctor_name']} ({result.get('department', 'Cardiology')}) "
            f"for {result.get('appointment_datetime')}."
        )
    else:
        assistant_reply = (
            f"The requested slot is occupied. Available alternative slots: "
            f"{', '.join(result.get('available_slots', []))}"
        )

    print(f"  [ASSISTANT REPLY] : {assistant_reply}")
    print("-" * 50)
    print(f"  [OK] Booking Status   : {result['status']}")
    if result["status"] == "BOOKED":
        print(f"  [OK] Appointment ID   : {result['appointment_id']}")
        print(f"  [OK] Assigned Doctor  : {result['doctor_name']}")
    print("=" * 50)
    print("  TEST PASSED: Booking request processed cleanly!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])