"""Rate limiting on auth endpoints (Redis counters, 429 + Retry-After)."""

CREDS = {"username": "bob", "email": "bob@example.com", "password": "s3cret-pass!"}


def _login(client, email="bob@example.com", password="wrong-password"):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def test_login_blocked_after_five_attempts_per_account(auth_client):
    for _ in range(5):
        assert _login(auth_client).status_code == 401  # wrong password, allowed
    r = _login(auth_client)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) > 0
    assert "Too many attempts" in r.json()["detail"]


def test_other_accounts_are_not_affected(auth_client):
    for _ in range(6):
        _login(auth_client)
    assert _login(auth_client, email="someone-else@example.com").status_code == 401


def test_register_limited_per_ip(auth_client):
    codes = []
    for i in range(6):
        r = auth_client.post(
            "/api/v1/auth/register",
            json={**CREDS, "username": f"bob{i}", "email": f"bob{i}@example.com"},
        )
        codes.append(r.status_code)
    assert codes[:5] == [201] * 5
    assert codes[5] == 429
