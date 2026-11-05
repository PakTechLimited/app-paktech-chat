"""Refresh-cookie flow: httpOnly cookie, rotation, replay detection, logout."""

CREDS = {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"}


def _register(auth_client):
    r = auth_client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 201
    return r


def test_login_sets_httponly_cookie_and_hides_refresh_from_body(auth_client):
    r = _register(auth_client)
    assert "refresh_token" not in r.json()
    set_cookie = r.headers["set-cookie"].lower()
    assert "pt_refresh=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie


def test_refresh_rotates_and_old_token_is_dead(auth_client):
    _register(auth_client)
    old = auth_client.cookies.get("pt_refresh", path="/api/v1/auth")
    assert old

    r = auth_client.post("/api/v1/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    new = auth_client.cookies.get("pt_refresh", path="/api/v1/auth")
    assert new and new != old

    # Replaying the OLD token must fail ...
    auth_client.cookies.clear()
    auth_client.cookies.set("pt_refresh", old, path="/api/v1/auth")
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401

    # ... and reuse detection revoked the new one too (all sessions killed).
    auth_client.cookies.clear()
    auth_client.cookies.set("pt_refresh", new, path="/api/v1/auth")
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_without_cookie_is_401(auth_client):
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_token_and_clears_cookie(auth_client):
    _register(auth_client)
    tok = auth_client.cookies.get("pt_refresh", path="/api/v1/auth")
    assert auth_client.post("/api/v1/auth/logout").status_code == 204
    auth_client.cookies.clear()
    auth_client.cookies.set("pt_refresh", tok, path="/api/v1/auth")
    assert auth_client.post("/api/v1/auth/refresh").status_code == 401
