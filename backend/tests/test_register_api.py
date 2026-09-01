"""CLI-visible tests for the signup endpoint.

Run from the project root:
    python -m pytest -s backend/tests/test_register_api.py

The ``-s`` option shows the created user and patient IDs in the terminal.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

# Allow both supported CLI forms:
#   python -m pytest -s backend/tests/test_register_api.py
#   python backend/tests/test_register_api.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from backend.database.db import SessionLocal
from backend.models.data_models import Patient, User
from main import app


client = TestClient(app)


def test_signup_creates_linked_user_and_patient() -> None:
    """A successful signup creates one User and one linked Patient profile."""
    unique_value = uuid4().hex[:12]
    signup_data = {
        "name": "CLI Signup Test",
        "email": f"cli-signup-{unique_value}@example.com",
        "phone": f"+91{uuid4().int % 10**10:010d}",
        "password": "Password123!",
    }

    response = client.post("/auth/signup", json=signup_data)

    assert response.status_code == 201, response.text
    body = response.json()
    user_id = body["user_id"]
    patient_id = body["patient_id"]

    # Visible when run with: python -m pytest -s backend/tests/test_register_api.py
    print(f"Created user_id={user_id}, patient_id={patient_id}")
    print(f"Signup response: {body}")

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


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main(["-s", __file__]))
