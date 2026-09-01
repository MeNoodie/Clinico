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


def get_auth_header():
    email = "appt_action_test@example.com"
    signup_data = {
        "name": "Appt Action Test Patient",
        "email": email,
        "phone": "+91-9955443322",
        "password": "Password123!",
    }
    client.post("/auth/signup", json=signup_data)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_start_session_reschedule_with_appointment_id():
    headers = get_auth_header()

    # Start session with RESCHEDULE_APPOINTMENT intent and appointment_id 1
    start_res = client.post("/chat/session/start", json={
        "intent": "RESCHEDULE_APPOINTMENT",
        "appointment_id": 1,
    }, headers=headers)

    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    # Greeting should acknowledge appointment #1
    assert "#1" in start_data["message"]

    session_id = start_data["session_id"]

    # First reply — appointment_id is already fulfilled, so it prompts for new date/time
    reply_res = client.post("/chat/session/reply", json={
        "session_id": session_id,
        "message": "2026-08-15T11:00:00",
    }, headers=headers)

    assert reply_res.status_code == 200
    reply_data = reply_res.json()
    assert "message" in reply_data


def test_start_session_cancel_with_appointment_id():
    headers = get_auth_header()

    # Start session with CANCEL_APPOINTMENT intent and appointment_id 1
    start_res = client.post("/chat/session/start", json={
        "intent": "CANCEL_APPOINTMENT",
        "appointment_id": 1,
    }, headers=headers)

    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "#1" in start_data["message"]


def test_start_session_followup_with_appointment_id():
    headers = get_auth_header()

    # Start session with FOLLOWUP_APPOINTMENT intent and appointment_id 1
    start_res = client.post("/chat/session/start", json={
        "intent": "FOLLOWUP_APPOINTMENT",
        "appointment_id": 1,
    }, headers=headers)

    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "#1" in start_data["message"]


if __name__ == "__main__":
    pytest.main([__file__])
