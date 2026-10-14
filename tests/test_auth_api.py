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


def test_signup_login_and_me_flow():
    unique = uuid4().hex[:8]
    email = f"auth_user_{unique}@example.com"
    phone = f"+91-{uuid4().int % 10**10:010d}"
    signup_data = {
        "name": "Auth Test User",
        "email": email,
        "phone": phone,
        "password": "Password123!",
    }

    print("\n" + "=" * 50)
    print("  TEST: Authentication Lifecycle (Signup -> Login -> /me)")
    print("=" * 50)

    # 1. Signup
    query_1 = f"POST /auth/signup: Register account for '{signup_data['name']}' ({email})"
    print(f"  [USER QUERY]      : {query_1}")
    signup_response = client.post("/auth/signup", json=signup_data)
    assert signup_response.status_code in (201, 409)
    signup_json = signup_response.json()
    reply_1 = f"[{signup_response.status_code} Created] User ID: {signup_json.get('user_id')}, Patient ID: {signup_json.get('patient_id')}"
    print(f"  [ASSISTANT REPLY] : {reply_1}")

    # 2. Login
    query_2 = f"POST /auth/login: Authenticate with email '{email}'"
    print(f"\n  [USER QUERY]      : {query_2}")
    login_response = client.post(
        "/auth/login",
        json={
            "email": signup_data["email"],
            "password": signup_data["password"],
        },
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    reply_2 = f"[{login_response.status_code} OK] Login successful. Access Token: {token[:25]}... (type: bearer)"
    print(f"  [ASSISTANT REPLY] : {reply_2}")

    # 3. Me
    query_3 = f"GET /auth/me: Retrieve current authenticated session profile"
    print(f"\n  [USER QUERY]      : {query_3}")
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == signup_data["email"]
    reply_3 = f"[{me_response.status_code} OK] Verified Identity: {me_data['email']}, Role: {me_data.get('role', 'patient')}"
    print(f"  [ASSISTANT REPLY] : {reply_3}")

    print("-" * 50)
    print("  [OK] Full authentication cycle completed successfully")
    print("=" * 50)
    print("  TEST PASSED: Full authentication lifecycle verified!")
    print("=" * 50 + "\n")


def test_login_invalid_credentials():
    print("\n" + "=" * 50)
    print("  TEST: Auth Security - Invalid Credentials Handling")
    print("=" * 50)

    user_query = "POST /auth/login: email='nonexistent@example.com', password='WrongPassword123!'"
    print(f"  [USER QUERY]      : {user_query}")
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    error_msg = response.json().get("detail", "Incorrect email or password")
    print(f"  [ASSISTANT REPLY] : [{response.status_code} Unauthorized] {error_msg}")

    print("-" * 50)
    print(f"  [OK] Rejection Status   : {response.status_code} Unauthorized")
    print("=" * 50)
    print("  TEST PASSED: Invalid credentials safely rejected!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
