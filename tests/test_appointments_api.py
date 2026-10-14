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


def test_appointments_history_unauthenticated():
    print("\n" + "=" * 50)
    print("  TEST: Appointment History - Unauthenticated Access")
    print("=" * 50)

    user_query = "GET /appointments/history (sent without Authorization header)"
    print(f"  [USER QUERY]      : {user_query}")

    res = client.get("/appointments/history")
    assert res.status_code in (401, 403)
    error_msg = res.json().get("detail", "Not authenticated")
    print(f"  [ASSISTANT REPLY] : [{res.status_code} Unauthorized] {error_msg}")

    print("-" * 50)
    print(f"  [OK] Guarded Status Code: {res.status_code}")
    print("=" * 50)
    print("  TEST PASSED: Endpoint properly rejects unauthorized calls!")
    print("=" * 50 + "\n")


def test_appointments_history_authenticated():
    print("\n" + "=" * 50)
    print("  TEST: Appointment History - Authenticated User")
    print("=" * 50)
    unique = uuid4().hex[:8]
    email = f"appt_test_{unique}@example.com"
    phone = f"+91-{uuid4().int % 10**10:010d}"
    signup_data = {
        "name": "Appt Test Patient",
        "email": email,
        "phone": phone,
        "password": "Password123!",
    }

    client.post("/auth/signup", json=signup_data)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user_query = f"GET /appointments/history (Bearer Token: {token[:20]}...)"
    print(f"  [USER QUERY]      : {user_query}")

    res = client.get("/appointments/history", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "history" in data
    assert isinstance(data["history"], list)

    records_count = len(data["history"])
    assistant_reply = (
        f"[200 OK] Retrieved appointment history for {email}: "
        f"Found {records_count} previous appointment(s)."
    )
    print(f"  [ASSISTANT REPLY] : {assistant_reply}")

    print("-" * 50)
    print(f"  [OK] Status Code     : {res.status_code} OK")
    print(f"  [OK] History Records : {records_count} items")
    print("=" * 50)
    print("  TEST PASSED: Patient appointment history retrieved!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
