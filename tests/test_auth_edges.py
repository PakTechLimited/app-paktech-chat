"""Auth failure paths: duplicates, bad credentials, token-type confusion, /me."""

import pytest

from app.core.security import create_access_token, create_refresh_token
from tests.helpers import PASSWORD, register

CREDS = {"username": "erin", "email": "erin@example.com", "password": PASSWORD}


def test_duplicate_email_or_username_is_a_conflict(auth_client):
    assert auth_client.post("/api/v1/auth/register", json=CREDS).status_code == 201
    same_email = {**CREDS, "username": "other"}
    same_name = {**CREDS, "email": "other@example.com"}
    for body in (same_email, same_name):
        assert auth_client.post("/api/v1/auth/register", json=body).status_code == 409


@pytest.mark.parametrize(
    "patch",
    [
        {"password": "short"},
        {"username": "a"},
        {"username": "bad name!"},
        {"email": "not-an-email"},
    ],
)
def test_registration_validation(auth_client, patch):
    r = auth_client.post("/api/v1/auth/register", json={**CREDS, **patch})
    assert r.status_code == 422


def test_login_failures_do_not_reveal_which_part_was_wrong(auth_client):
    auth_client.post("/api/v1/auth/register", json=CREDS)
    wrong_pw = auth_client.post(
        "/api/v1/auth/login", json={"email": CREDS["email"], "password": "nope-nope"}
    )
    unknown = auth_client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
    )
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_me_returns_the_profile_without_secrets(auth_client):
    h = register(auth_client, "erin")
    me = auth_client.get("/api/v1/auth/me", headers=h).json()
    assert me["username"] == "erin" and me["email"] == "erin@example.com"
    assert me["role"] == "member"
    assert "hashed_password" not in me


@pytest.mark.parametrize(
    "header",
    [
        {},
        {"Authorization": "Bearer not.a.jwt"},
        {"Authorization": "Basic abc"},
    ],
)
def test_me_rejects_missing_or_garbage_credentials(auth_client, header):
    assert auth_client.get("/api/v1/auth/me", headers=header).status_code == 401


def test_a_refresh_token_is_not_accepted_as_an_access_token(auth_client):
    register(auth_client, "erin")
    refresh, _ = create_refresh_token(1)
    r = auth_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert r.status_code == 401


def test_an_access_token_is_not_accepted_as_a_refresh_cookie(auth_client):
    register(auth_client, "erin")
    auth_client.cookies.clear()
    auth_client.cookies.set("pt_refresh", create_access_token(1), path="/api/v1/auth")
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401


def test_token_for_a_deleted_user_is_rejected(auth_client):
    token = create_access_token(4242)
    r = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_logout_ends_the_session_and_is_safe_to_repeat(auth_client):
    register(auth_client, "erin")
    assert auth_client.post("/api/v1/auth/logout").status_code == 204
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401
    assert auth_client.post("/api/v1/auth/logout").status_code == 204
