"""Admin API: role gating, user management, stats, and what deactivation cuts off."""

import pytest

from tests.helpers import PASSWORD, promote, register, user_id

ADMIN_ENDPOINTS = [
    ("get", "/api/v1/admin/users"),
    ("get", "/api/v1/admin/stats"),
    ("patch", "/api/v1/admin/users/1/deactivate"),
    ("patch", "/api/v1/admin/users/1/activate"),
    ("delete", "/api/v1/admin/posts/1"),
]


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_anonymous_is_rejected(auth_client, method, path):
    assert getattr(auth_client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_members_are_forbidden(auth_client, method, path):
    h = register(auth_client, "member")
    assert getattr(auth_client, method)(path, headers=h).status_code == 403


def test_role_is_read_live_from_the_database(auth_client):
    """A token issued before promotion works as admin right after it."""
    h = register(auth_client, "boss")
    assert auth_client.get("/api/v1/admin/stats", headers=h).status_code == 403
    promote("boss")
    assert auth_client.get("/api/v1/admin/stats", headers=h).status_code == 200


def test_list_users_never_exposes_password_hashes(auth_client):
    h = register(auth_client, "boss")
    register(auth_client, "alice")
    promote("boss")
    users = auth_client.get("/api/v1/admin/users", headers=h).json()
    assert {u["username"] for u in users} == {"boss", "alice"}
    assert all("hashed_password" not in u and "password" not in u for u in users)
    assert {u["role"] for u in users} == {"admin", "member"}


def test_stats_count_users_messages_and_posts(auth_client):
    h = register(auth_client, "boss")
    register(auth_client, "alice")
    promote("boss")
    auth_client.post("/api/v1/posts/", json={"content": "hi"}, headers=h)
    auth_client.post(
        "/api/v1/messages/", json={"content": "yo", "room_id": 1}, headers=h
    )
    stats = auth_client.get("/api/v1/admin/stats", headers=h).json()
    assert stats == {
        "total_users": 2,
        "active_users": 2,
        "total_messages": 1,
        "total_posts": 1,
    }


def test_admin_cannot_deactivate_themselves(auth_client):
    h = register(auth_client, "boss")
    promote("boss")
    me = user_id(auth_client, h)
    r = auth_client.patch(f"/api/v1/admin/users/{me}/deactivate", headers=h)
    assert r.status_code == 400


def test_unknown_user_and_post_are_404(auth_client):
    h = register(auth_client, "boss")
    promote("boss")
    assert (
        auth_client.patch("/api/v1/admin/users/999/deactivate", headers=h).status_code
        == 404
    )
    assert (
        auth_client.patch("/api/v1/admin/users/999/activate", headers=h).status_code
        == 404
    )
    assert auth_client.delete("/api/v1/admin/posts/999", headers=h).status_code == 404


def test_deactivation_cuts_off_every_way_back_in(auth_client):
    admin = register(auth_client, "boss")
    promote("boss")
    victim = register(auth_client, "victim")  # last signup: its cookie is in the jar
    victim_id = user_id(auth_client, victim)

    r = auth_client.patch(f"/api/v1/admin/users/{victim_id}/deactivate", headers=admin)
    assert r.json() == {"id": victim_id, "is_active": False}

    # the access token still in their browser stops working at once
    assert auth_client.get("/api/v1/auth/me", headers=victim).status_code == 401
    # their refresh session was revoked, so they cannot silently renew
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401
    # and logging in again is refused
    r = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": PASSWORD},
    )
    assert r.status_code == 403


def test_activation_restores_access(auth_client):
    admin = register(auth_client, "boss")
    promote("boss")
    register(auth_client, "victim")
    victim_id = 2
    auth_client.patch(f"/api/v1/admin/users/{victim_id}/deactivate", headers=admin)
    r = auth_client.patch(f"/api/v1/admin/users/{victim_id}/activate", headers=admin)
    assert r.json() == {"id": victim_id, "is_active": True}
    r = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": PASSWORD},
    )
    assert r.status_code == 200
