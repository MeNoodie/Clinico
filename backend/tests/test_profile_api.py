from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import app

client = TestClient(app)


def test_get_user_profile():
    # Register a user to fetch
    email = "get_user_profile@example.com"
    phone = "+91-9870001111"
    signup_res = client.post("/auth/signup", json={
        "name": "Profile User",
        "email": email,
        "phone": phone,
        "password": "Password123!",
    })
    assert signup_res.status_code in (201, 409)
    user_id = signup_res.json()["user_id"] if signup_res.status_code == 201 else 1

    # Fetch user profile
    res = client.get(f"/users/{user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user_id
    assert "name" in data
    assert "email" in data
    assert "phone" in data


def test_get_user_profile_not_found():
    res = client.get("/users/999999")
    assert res.status_code == 404


def test_update_user_profile_name_email_phone():
    # Register a new user
    email = "update_user_initial@example.com"
    phone = "+91-9870002222"
    signup_res = client.post("/auth/signup", json={
        "name": "Initial Name",
        "email": email,
        "phone": phone,
        "password": "Password123!",
    })
    assert signup_res.status_code == 201
    user_id = signup_res.json()["user_id"]

    # Patch update: name, email, phone
    new_email = "update_user_changed@example.com"
    new_phone = "+91-9870003333"
    patch_res = client.patch(f"/users/{user_id}", json={
        "name": "Changed Name",
        "email": new_email,
        "phone": new_phone,
    })
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["id"] == user_id
    assert updated["name"] == "Changed Name"
    assert updated["email"] == new_email
    assert updated["phone"] == new_phone

    # Verify GET returns updated data
    get_res = client.get(f"/users/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Changed Name"


def test_update_user_profile_conflict():
    # Register User A
    user_a_res = client.post("/auth/signup", json={
        "name": "User A",
        "email": "user_a@example.com",
        "phone": "+91-9870004444",
        "password": "Password123!",
    })
    assert user_a_res.status_code in (201, 409)
    user_a_email = "user_a@example.com"

    # Register User B
    user_b_res = client.post("/auth/signup", json={
        "name": "User B",
        "email": "user_b@example.com",
        "phone": "+91-9870005555",
        "password": "Password123!",
    })
    assert user_b_res.status_code in (201, 409)
    if user_b_res.status_code == 201:
        user_b_id = user_b_res.json()["user_id"]
        # Try updating User B's email to User A's email (should fail with 409)
        conflict_res = client.patch(f"/users/{user_b_id}", json={"email": user_a_email})
        assert conflict_res.status_code == 409


if __name__ == "__main__":
    pytest.main([__file__])
