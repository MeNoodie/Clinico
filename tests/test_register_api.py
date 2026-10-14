"""CLI-visible tests for the signup endpoint.

Run from the project root:
    python -m pytest -s tests/test_register_api.py
    python tests/test_register_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

# Ensure project root is in sys.path when running scripts directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.database.db import SessionLocal
from backend.main import app
from backend.models.data_models import Patient, User

client = TestClient(app)


def test_signup_creates_linked_user_and_patient() -> None:
    """A successful signup creates one User and one linked Patient profile."""
    unique_value = uuid4().hex[:10]
    signup_data = {
        "name": "CLI Signup Test Patient",
        "email": f"cli-signup-{unique_value}@example.com",
        "phone": f"+91-{uuid4().int % 10**10:010d}",
        "password": "Password123!",
    }

    user_query = (
        f"POST /auth/signup: Register patient '{signup_data['name']}', "
        f"Email: {signup_data['email']}, Phone: {signup_data['phone']}"
    )

    print("\n" + "=" * 50)
    print("  TEST: Registration - User & Linked Patient Creation")
    print("=" * 50)
    print(f"  [USER QUERY]      : {user_query}")

    response = client.post("/auth/signup", json=signup_data)

    assert response.status_code == 201, response.text
    body = response.json()
    user_id = body["user_id"]
    patient_id = body["patient_id"]

    assistant_reply = (
        f"[{response.status_code} Created] Account created successfully! "
        f"User ID #{user_id}, Linked Patient ID #{patient_id}, Bearer Token generated."
    )
    print(f"  [ASSISTANT REPLY] : {assistant_reply}")

    assert isinstance(user_id, int)
    assert isinstance(patient_id, int)
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    with SessionLocal() as db:
        user = db.get(User, user_id)
        patient = db.get(Patient, patient_id)

        assert user is not None
        assert patient is not None
        assert user.email == signup_data["email"]
        assert user.phone == signup_data["phone"]
        assert patient.user_id == user.id
        assert patient.name == user.name
        assert patient.email == user.email
        assert patient.phone == user.phone

    print("-" * 50)
    print(f"  [OK] User Record In DB   : {user.email}")
    print(f"  [OK] Patient Record In DB: {patient.name} (linked to user #{user.id})")
    print("=" * 50)
    print("  TEST PASSED: User & patient linked successfully in DB!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-s", "-v", __file__]))
