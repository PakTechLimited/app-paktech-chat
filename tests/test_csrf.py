"""Cookie-authenticated auth endpoints require the CSRF header and a good Origin."""

import pytest

from app.core.config import settings

CREDS = {"username": "carol", "email": "carol@example.com", "password": "Passw0rd!x"}
ENDPOINTS = ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout"]


def test_register_and_login_work_with_the_header(auth_client):
    assert auth_client.post("/api/v1/auth/register", json=CREDS).status_code == 201
    login = {"email": CREDS["email"], "password": CREDS["password"]}
    assert auth_client.post("/api/v1/auth/login", json=login).status_code == 200


def test_register_without_header_is_rejected(auth_client):
    res = auth_client.post(
        "/api/v1/auth/register", json=CREDS, headers={"X-Requested-With": ""}
    )
    assert res.status_code == 403
    # nothing was created: the same registration succeeds afterwards
    assert auth_client.post("/api/v1/auth/register", json=CREDS).status_code == 201


@pytest.mark.parametrize("path", ENDPOINTS)
def test_missing_header_is_rejected(auth_client, path):
    res = auth_client.post(path, json={}, headers={"X-Requested-With": ""})
    assert res.status_code == 403


@pytest.mark.parametrize("path", ENDPOINTS)
def test_foreign_origin_is_rejected(auth_client, path):
    res = auth_client.post(path, json={}, headers={"Origin": "https://evil.example"})
    assert res.status_code == 403


def test_logout_from_foreign_origin_keeps_the_session(auth_client):
    """A cross-site logout must not consume the victim's refresh token."""
    auth_client.post("/api/v1/auth/register", json=CREDS)
    res = auth_client.post(
        "/api/v1/auth/logout", headers={"Origin": "https://evil.example"}
    )
    assert res.status_code == 403
    assert auth_client.post("/api/v1/auth/refresh").status_code == 200


def test_allowed_origin_passes(auth_client):
    origin = settings.cors_origins[0]
    auth_client.post("/api/v1/auth/register", json=CREDS)
    res = auth_client.post("/api/v1/auth/refresh", headers={"Origin": origin})
    assert res.status_code == 200
