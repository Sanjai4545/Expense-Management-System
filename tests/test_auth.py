from datetime import datetime, timezone, timedelta
import jwt
import pytest
from app.config import SECRET_KEY
from tests.conftest import signup


def test_signup_login_me_success(client):
    # 1. Signup succeeds with 201
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Sanjai", "email": "Sanjai@example.com", "password": "Password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["name"] == "Sanjai"
    assert data["user"]["email"] == "sanjai@example.com"
    assert "password_hash" not in data["user"]
    token = data["token"]

    # 2. Login succeeds with 200
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "sanjai@example.com", "password": "Password123"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "token" in login_data
    assert login_data["user"]["email"] == "sanjai@example.com"

    # 3. GET /me returns the user without password_hash
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == data["user"]["id"]
    assert me_data["name"] == "Sanjai"
    assert me_data["email"] == "sanjai@example.com"
    assert "password_hash" not in me_data


def test_duplicate_email_including_case(client):
    client.post(
        "/api/auth/signup",
        json={"name": "User One", "email": "User@example.com", "password": "Password123"},
    )
    # Different case
    resp = client.post(
        "/api/auth/signup",
        json={"name": "User Two", "email": "user@EXAMPLE.COM", "password": "Password123"},
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "conflict"
    assert body["error"]["message"] == "An account with this email already exists."


def test_wrong_password_and_unknown_email_same_message(client):
    client.post(
        "/api/auth/signup",
        json={"name": "User One", "email": "user@example.com", "password": "Password123"},
    )

    # Wrong password
    resp1 = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "WrongPassword"},
    )
    assert resp1.status_code == 401
    body1 = resp1.json()

    # Unknown email
    resp2 = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "Password123"},
    )
    assert resp2.status_code == 401
    body2 = resp2.json()

    assert body1["error"]["message"] == "Incorrect email or password."
    assert body2["error"]["message"] == "Incorrect email or password."
    assert body1["error"]["message"] == body2["error"]["message"]


def test_password_shorter_than_8(client):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "User One", "email": "user@example.com", "password": "123"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert "fields" in body["error"]
    assert "password" in body["error"]["fields"]


def test_missing_or_garbage_token(client):
    # Missing token
    resp1 = client.get("/api/auth/me")
    assert resp1.status_code == 401
    assert resp1.json()["error"]["code"] == "unauthorized"

    # Garbage token
    resp2 = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage-token-12345"})
    assert resp2.status_code == 401
    assert resp2.json()["error"]["code"] == "unauthorized"


def test_expired_token(client):
    past_exp = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    expired_token = jwt.encode({"sub": "1", "exp": past_exp}, SECRET_KEY, algorithm="HS256")

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"
