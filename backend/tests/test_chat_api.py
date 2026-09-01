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
    email = "chat_test_patient@example.com"
    signup_data = {
        "name": "Chat Test Patient",
        "email": email,
        "phone": "+91-9988776655",
        "password": "Password123!",
    }
    client.post("/auth/signup", json=signup_data)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_chat_unauthenticated_access():
    res = client.post("/chat/appointments", json={"message": "I need a doctor"})
    assert res.status_code in (401, 403)

    res = client.post("/chat/session/start", json={"intent": "BOOK_APPOINTMENT"})
    assert res.status_code in (401, 403)


def test_chat_session_lifecycle():
    headers = get_auth_header()

    start_res = client.post("/chat/session/start", json={"intent": "BOOK_APPOINTMENT"}, headers=headers)
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "message" in start_data

    bad_reply = client.post("/chat/session/reply", json={
        "session_id": "nonexistent-session-id",
        "message": "hello",
    }, headers=headers)
    assert bad_reply.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__])
