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


def _register_and_login(name: str = "Test User") -> tuple[int, dict[str, str], dict[str, str]]:
    unique = uuid4().hex[:8]
    email = f"user_{unique}@example.com"
    phone = f"+91-{uuid4().int % 10**10:010d}"
    password = "Password123!"

    signup_res = client.post(
        "/auth/signup",
        json={
            "name": name,
            "email": email,
            "phone": phone,
            "password": password,
        },
    )
    assert signup_res.status_code == 201
    user_id = signup_res.json()["user_id"]

    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return user_id, headers, {"name": name, "email": email, "phone": phone}


def test_get_user_profile():
    print("\n" + "=" * 50)
    print("  TEST: User Profile - Authenticated Fetch by ID")
    print("=" * 50)
    user_id, headers, user_data = _register_and_login("Profile User")

    user_query = f"GET /users/{user_id} (Bearer Token of User #{user_id})"
    print(f"  [USER QUERY]      : {user_query}")

    res = client.get(f"/users/{user_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user_id
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]
    assert data["phone"] == user_data["phone"]

    assistant_reply = (
        f"[{res.status_code} OK] Profile found: ID={data['id']}, Name='{data['name']}', "
        f"Email='{data['email']}', Phone='{data['phone']}'"
    )
    print(f"  [ASSISTANT REPLY] : {assistant_reply}")

    print("-" * 50)
    print("  [OK] Profile retrieved and matched token identity")
    print("=" * 50)
    print("  TEST PASSED: User profile retrieved successfully!")
    print("=" * 50 + "\n")


def test_get_user_profile_unauthenticated():
    print("\n" + "=" * 50)
    print("  TEST: User Profile - Unauthenticated Protection (401)")
    print("=" * 50)

    user_query = "GET /users/1 (sent without Authorization header)"
    print(f"  [USER QUERY]      : {user_query}")
    res = client.get("/users/1")
    assert res.status_code in (401, 403)
    error_msg = res.json().get("detail", "Not authenticated")
    print(f"  [ASSISTANT REPLY] : [{res.status_code} Unauthorized] {error_msg}")

    print("-" * 50)
    print(f"  [OK] Guarded Status Code: {res.status_code}")
    print("=" * 50)
    print("  TEST PASSED: Unauthenticated profile requests are blocked!")
    print("=" * 50 + "\n")


def test_get_user_profile_forbidden_for_other_user():
    print("\n" + "=" * 50)
    print("  TEST: User Profile - Cross-User Access Guard (403)")
    print("=" * 50)
    user_id, headers, _ = _register_and_login("Owner User")
    other_id = user_id + 9999

    user_query = f"GET /users/{other_id} (User #{user_id} attempting to view User #{other_id}'s profile)"
    print(f"  [USER QUERY]      : {user_query}")
    res = client.get(f"/users/{other_id}", headers=headers)
    assert res.status_code == 403
    error_msg = res.json().get("detail", "You can only access your own profile")
    print(f"  [ASSISTANT REPLY] : [{res.status_code} Forbidden] {error_msg}")

    print("-" * 50)
    print("  [OK] Cross-user profile access safely blocked")
    print("=" * 50)
    print("  TEST PASSED: Users cannot access other profiles!")
    print("=" * 50 + "\n")


def test_update_user_profile_name_email_phone():
    print("\n" + "=" * 50)
    print("  TEST: User Profile - Update Name, Email & Phone")
    print("=" * 50)
    user_id, headers, _ = _register_and_login("Initial Name")

    unique = uuid4().hex[:8]
    new_email = f"update_mod_{unique}@example.com"
    new_phone = f"+91-{uuid4().int % 10**10:010d}"

    user_query = (
        f"PATCH /users/{user_id}: Change name to 'Changed Name', "
        f"email to '{new_email}', phone to '{new_phone}'"
    )
    print(f"  [USER QUERY]      : {user_query}")

    patch_res = client.patch(
        f"/users/{user_id}",
        json={
            "name": "Changed Name",
            "email": new_email,
            "phone": new_phone,
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["id"] == user_id
    assert updated["name"] == "Changed Name"
    assert updated["email"] == new_email
    assert updated["phone"] == new_phone

    assistant_reply = (
        f"[{patch_res.status_code} OK] Profile updated: Name='{updated['name']}', "
        f"Email='{updated['email']}', Phone='{updated['phone']}'"
    )
    print(f"  [ASSISTANT REPLY] : {assistant_reply}")

    print("-" * 50)
    print(f"  [OK] Verified Name    : {updated['name']}")
    print(f"  [OK] Verified Email   : {updated['email']}")
    print("=" * 50)
    print("  TEST PASSED: User profile updated and verified!")
    print("=" * 50 + "\n")


def test_update_user_profile_conflict():
    print("\n" + "=" * 50)
    print("  TEST: User Profile - Email Conflict Prevention (409)")
    print("=" * 50)
    user_a_id, _, user_a_data = _register_and_login("User A")
    user_b_id, headers_b, _ = _register_and_login("User B")

    user_query = (
        f"PATCH /users/{user_b_id}: User B attempting to change email "
        f"to '{user_a_data['email']}' (already owned by User A)"
    )
    print(f"  [USER QUERY]      : {user_query}")

    conflict_res = client.patch(
        f"/users/{user_b_id}",
        json={"email": user_a_data["email"]},
        headers=headers_b,
    )
    assert conflict_res.status_code == 409
    error_msg = conflict_res.json().get("detail", "Email is already registered by another user")
    print(f"  [ASSISTANT REPLY] : [{conflict_res.status_code} Conflict] {error_msg}")

    print("-" * 50)
    print("  [OK] Duplicate email conflict correctly rejected")
    print("=" * 50)
    print("  TEST PASSED: Duplicate email update safely rejected!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
