from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path when running scripts directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app

client = TestClient(app)


def get_auth_header() -> dict[str, str]:
    email = f"appt_action_{uuid4().hex[:8]}@example.com"
    phone = f"+91-{uuid4().int % 10**10:010d}"
    signup_data = {
        "name": "Appt Action Test Patient",
        "email": email,
        "phone": phone,
        "password": "Password123!",
    }
    client.post("/auth/signup", json=signup_data)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_start_session_reschedule_with_appointment_id():
    print("\n" + "=" * 50)
    print("  TEST: Session - Reschedule Appointment (#1)")
    print("=" * 50)
    headers = get_auth_header()

    query_1 = "Start session: Intent=RESCHEDULE_APPOINTMENT, Appointment ID=1"
    print(f"  [USER QUERY]      : {query_1}")
    start_res = client.post(
        "/chat/session/start",
        json={
            "intent": "RESCHEDULE_APPOINTMENT",
            "appointment_id": 1,
        },
        headers=headers,
    )

    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "#1" in start_data["message"]
    session_id = start_data["session_id"]
    print(f"  [ASSISTANT REPLY] : {start_data['message']}")

    query_2 = "2026-11-20T11:00:00"
    print(f"\n  [USER QUERY]      : {query_2}")
    reply_res = client.post(
        "/chat/session/reply",
        json={
            "session_id": session_id,
            "message": query_2,
        },
        headers=headers,
    )

    assert reply_res.status_code == 200
    reply_data = reply_res.json()
    assert "message" in reply_data
    print(f"  [ASSISTANT REPLY] : {reply_data['message']}")

    print("-" * 50)
    print(f"  [OK] Session ID   : {session_id}")
    print(f"  [OK] Status Code  : {reply_res.status_code} OK")
    print("=" * 50)
    print("  TEST PASSED: Reschedule session completed successfully!")
    print("=" * 50 + "\n")


def test_start_session_cancel_with_appointment_id():
    print("\n" + "=" * 50)
    print("  TEST: Session - Cancel Appointment (#1)")
    print("=" * 50)
    headers = get_auth_header()

    user_query = "Start session: Intent=CANCEL_APPOINTMENT, Appointment ID=1"
    print(f"  [USER QUERY]      : {user_query}")
    start_res = client.post(
        "/chat/session/start",
        json={
            "intent": "CANCEL_APPOINTMENT",
            "appointment_id": 1,
        },
        headers=headers,
    )

    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "#1" in start_data["message"]

    print(f"  [ASSISTANT REPLY] : {start_data['message']}")
    print("-" * 50)
    print(f"  [OK] Session ID   : {start_data['session_id']}")
    print(f"  [OK] Status Code  : {start_res.status_code} OK")
    print("=" * 50)
    print("  TEST PASSED: Cancel session initialized successfully!")
    print("=" * 50 + "\n")


def test_start_session_followup_with_appointment_id():
    print("\n" + "=" * 50)
    print("  TEST: Session - Follow-up Appointment (#1)")
    print("=" * 50)
    headers = get_auth_header()

    user_query = "Start session: Intent=FOLLOWUP_APPOINTMENT, Appointment ID=1"
    print(f"  [USER QUERY]      : {user_query}")
    start_res = client.post(
        "/chat/session/start",
        json={
            "intent": "FOLLOWUP_APPOINTMENT",
            "appointment_id": 1,
        },
        headers=headers,
    )

    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "#1" in start_data["message"]

    print(f"  [ASSISTANT REPLY] : {start_data['message']}")
    print("-" * 50)
    print(f"  [OK] Session ID   : {start_data['session_id']}")
    print(f"  [OK] Status Code  : {start_res.status_code} OK")
    print("=" * 50)
    print("  TEST PASSED: Follow-up session initialized successfully!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
