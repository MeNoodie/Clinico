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
    unique = uuid4().hex[:8]
    email = f"chat_test_{unique}@example.com"
    phone = f"+91-{uuid4().int % 10**10:010d}"
    signup_data = {
        "name": "Chat Test Patient",
        "email": email,
        "phone": phone,
        "password": "Password123!",
    }
    client.post("/auth/signup", json=signup_data)
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_chat_unauthenticated_access():
    print("\n" + "=" * 50)
    print("  TEST: Chat API - Unauthorized Access Guard")
    print("=" * 50)

    user_query_1 = "I need a doctor (sent without auth token)"
    print(f"  [USER QUERY]      : {user_query_1}")
    res = client.post("/chat/appointments", json={"message": "I need a doctor"})
    assert res.status_code in (401, 403)
    error_msg = res.json().get("detail", "Unauthorized")
    print(f"  [ASSISTANT REPLY] : [{res.status_code} Unauthorized] {error_msg}")

    user_query_2 = "Start session: Intent=BOOK_APPOINTMENT (sent without auth token)"
    print(f"\n  [USER QUERY]      : {user_query_2}")
    res2 = client.post("/chat/session/start", json={"intent": "BOOK_APPOINTMENT"})
    assert res2.status_code in (401, 403)
    error_msg2 = res2.json().get("detail", "Unauthorized")
    print(f"  [ASSISTANT REPLY] : [{res2.status_code} Unauthorized] {error_msg2}")

    print("-" * 50)
    print("  [OK] Both unauthenticated requests safely blocked")
    print("=" * 50)
    print("  TEST PASSED: Chat endpoints guarded against unauthorized access!")
    print("=" * 50 + "\n")


def test_chat_session_lifecycle():
    print("\n" + "=" * 50)
    print("  TEST: Chat Session - Lifecycle (Start & Reply)")
    print("=" * 50)
    headers = get_auth_header()

    user_query_1 = "Start guided session: Intent=BOOK_APPOINTMENT"
    print(f"  [USER QUERY]      : {user_query_1}")
    start_res = client.post(
        "/chat/session/start",
        json={"intent": "BOOK_APPOINTMENT"},
        headers=headers,
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "message" in start_data

    session_id = start_data["session_id"]
    print(f"  [ASSISTANT REPLY] : {start_data['message']}")

    user_query_2 = "hello (sent to invalid session_id: 'nonexistent-session-id')"
    print(f"\n  [USER QUERY]      : {user_query_2}")
    bad_reply = client.post(
        "/chat/session/reply",
        json={
            "session_id": "nonexistent-session-id",
            "message": "hello",
        },
        headers=headers,
    )
    assert bad_reply.status_code == 404
    error_reply = bad_reply.json().get("detail", "Session not found")
    print(f"  [ASSISTANT REPLY] : [{bad_reply.status_code} Not Found] {error_reply}")

    print("-" * 50)
    print(f"  [OK] Session ID   : {session_id}")
    print(f"  [OK] Status Code  : {start_res.status_code} OK")
    print("=" * 50)
    print("  TEST PASSED: Chat session lifecycle verified successfully!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
