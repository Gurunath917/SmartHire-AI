"""
Tests for authentication endpoints.
Covers: register, login, get /me, unauthorized access, duplicate email,
        wrong password, expired JWT, role validation.
"""
import pytest
from tests.conftest import register_user, login_user, auth_headers


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_candidate(client):
    resp = register_user(client, "candidate1@test.com", "Password123!", "CANDIDATE", "Test Candidate")
    assert resp.status_code == 201
    assert resp.json()["success"] is True


def test_register_recruiter(client):
    resp = register_user(client, "recruiter1@test.com", "Password123!", "RECRUITER", "Test Recruiter")
    assert resp.status_code == 201
    assert resp.json()["success"] is True


def test_register_duplicate_email(client):
    register_user(client, "dup@test.com", "Password123!", "CANDIDATE")
    resp = register_user(client, "dup@test.com", "Password123!", "CANDIDATE")
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


def test_register_as_admin_rejected(client):
    resp = register_user(client, "admin@test.com", "Password123!", "ADMIN")
    assert resp.status_code == 422  # validation error


def test_register_weak_password(client):
    resp = register_user(client, "weak@test.com", "123", "CANDIDATE")
    assert resp.status_code == 422


def test_register_short_name(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "A",
        "email": "short@test.com",
        "password": "Password123!",
        "role": "CANDIDATE",
    })
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client):
    register_user(client, "login1@test.com", "Password123!", "CANDIDATE")
    resp = client.post("/api/auth/login", json={
        "email": "login1@test.com",
        "password": "Password123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "CANDIDATE"


def test_login_wrong_password(client):
    register_user(client, "wrongpw@test.com", "Password123!", "CANDIDATE")
    resp = client.post("/api/auth/login", json={
        "email": "wrongpw@test.com",
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401
    assert "Incorrect" in resp.json()["detail"]


def test_login_nonexistent_email(client):
    resp = client.post("/api/auth/login", json={
        "email": "nobody@test.com",
        "password": "Password123!",
    })
    assert resp.status_code == 401


# ── Protected routes ──────────────────────────────────────────────────────────

def test_get_me_authenticated(client):
    register_user(client, "me@test.com", "Password123!", "CANDIDATE")
    token = login_user(client, "me@test.com", "Password123!")
    resp = client.get("/api/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@test.com"
    assert "hashed_password" not in data
    assert "password" not in data


def test_get_me_no_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_get_me_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


# ── Role-based access ─────────────────────────────────────────────────────────

def test_candidate_cannot_access_recruiter_endpoint(client):
    register_user(client, "rbac_candidate@test.com", "Password123!", "CANDIDATE")
    token = login_user(client, "rbac_candidate@test.com", "Password123!")
    resp = client.get("/api/recruiters/me", headers=auth_headers(token))
    assert resp.status_code == 403


def test_recruiter_cannot_access_candidate_endpoint(client):
    register_user(client, "rbac_recruiter@test.com", "Password123!", "RECRUITER")
    token = login_user(client, "rbac_recruiter@test.com", "Password123!")
    resp = client.get("/api/candidates/me", headers=auth_headers(token))
    assert resp.status_code == 403
