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


def test_signup_login_and_me_flow():
    unique_suffix = "test_user_99@example.com"
    signup_data = {
        "name": "Test User",
        "email": unique_suffix,
        "phone": "+91-9900000099",
        "password": "Password123!",
    }

    signup_response = client.post("/auth/signup", json=signup_data)
    assert signup_response.status_code in (201, 409)

    login_response = client.post("/auth/login", json={
        "email": signup_data["email"],
        "password": signup_data["password"],
    })
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == signup_data["email"]


def test_login_invalid_credentials():
    response = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])
