from __future__ import annotations
import sys
from pathlib import Path

# Ensure project root is in sys.path when running scripts directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_appointments_history_unauthenticated():
    res = client.get("/appointments/history")
    assert res.status_code in (401, 403)


def test_appointments_history_authenticated():
    email = "appt_test_patient@example.com"
    signup_data = {
        "name": "Appt Test Patient",
        "email": email,
        "phone": "+91-9911223344",
        "password": "Password123!",
    }
    client.post("/auth/signup", json=signup_data)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/appointments/history", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "history" in data
    assert isinstance(data["history"], list)


if __name__ == "__main__":
    pytest.main([__file__])
