"""Failure behaviour: Redis down, dependency health, malformed WebSocket frames."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import health
from app.core import rate_limit
from app.core.config import settings
from tests.helpers import register
from tests.test_chat import ENGINEERING, _open, _token, _until

pytestmark = pytest.mark.timeout(20)


# --- rate limiter -----------------------------------------------------------


def test_rate_limiter_fails_open_when_redis_is_down(monkeypatch):
    """A Redis outage must not lock everyone out of login."""

    async def boom():
        raise ConnectionError("redis down")

    monkeypatch.setattr(rate_limit, "get_redis", boom)

    async def hammer():
        for _ in range(10):  # limit is 1: would be blocked if it counted
            await rate_limit.enforce("k", limit=1, window_seconds=60)

    asyncio.run(hammer())


def test_rate_limiter_can_be_switched_off(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    h = register(auth_client, "alice")
    codes = {
        auth_client.post(
            "/api/v1/rooms/", json={"name": f"r{i}"}, headers=h
        ).status_code
        for i in range(8)  # the limit is 5 per hour
    }
    assert codes == {201}


def test_limit_exceeded_carries_retry_after(auth_client):
    h = register(auth_client, "alice")
    for i in range(5):
        auth_client.post("/api/v1/rooms/", json={"name": f"r{i}"}, headers=h)
    r = auth_client.post("/api/v1/rooms/", json={"name": "late"}, headers=h)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


# --- health -----------------------------------------------------------------


class _FakeConn:
    def __init__(self, fail):
        self.fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def execute(self, *_):
        if self.fail:
            raise ConnectionError("postgres down")


class _FakeEngine:
    def __init__(self, fail):
        self.fail = fail

    def connect(self):
        return _FakeConn(self.fail)


class _FakeRedis:
    def __init__(self, fail):
        self.fail = fail

    async def ping(self):
        if self.fail:
            raise ConnectionError("redis down")


def _health(monkeypatch, pg_fails, redis_fails):
    async def get_redis():
        return _FakeRedis(redis_fails)

    monkeypatch.setattr(health, "engine", _FakeEngine(pg_fails))
    monkeypatch.setattr(health, "get_redis", get_redis)
    app = FastAPI()
    app.include_router(health.router, prefix="/api/v1")
    return TestClient(app).get("/api/v1/health")


@pytest.mark.parametrize(
    "pg_fails,redis_fails,expected",
    [
        (False, False, (200, "healthy", "ok", "ok")),
        (True, False, (503, "degraded", "error", "ok")),
        (False, True, (503, "degraded", "ok", "error")),
        (True, True, (503, "degraded", "error", "error")),
    ],
)
def test_health_reports_each_dependency(monkeypatch, pg_fails, redis_fails, expected):
    r = _health(monkeypatch, pg_fails, redis_fails)
    body = r.json()
    code, status, pg, rd = expected
    assert (r.status_code, body["status"]) == (code, status)
    assert (body["checks"]["postgres"], body["checks"]["redis"]) == (pg, rd)


# --- WebSocket robustness ---------------------------------------------------


def test_malformed_frames_get_errors_and_do_not_kill_the_socket(auth_client):
    token = _token(
        auth_client,
        {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"},
    )
    ws, sock = _open(auth_client, token)
    try:
        _until(sock, "ready")
        sock.send_text("this is not json")
        assert "Invalid JSON" in _until(sock, "error")["content"]
        sock.send_text("[1, 2, 3]")
        assert "Invalid message" in _until(sock, "error")["content"]
        sock.send_json({"type": "message", "content": "x" * 4001})
        assert "too long" in _until(sock, "error")["content"]
        sock.send_json({"type": "message", "content": "   "})  # ignored, no error
        sock.send_json({"type": "message", "content": "still alive"})
        assert _until(sock, "message")["content"] == "still alive"
    finally:
        ws.__exit__(None, None, None)


def test_unknown_frame_types_are_ignored(auth_client):
    token = _token(
        auth_client,
        {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"},
    )
    ws, sock = _open(auth_client, token, ENGINEERING)
    try:
        _until(sock, "ready")
        sock.send_json({"type": "launch-missiles"})
        sock.send_json({"type": "message", "content": "after the weird one"})
        assert _until(sock, "message")["content"] == "after the weird one"
    finally:
        ws.__exit__(None, None, None)


def test_message_flood_is_throttled_not_fatal(auth_client):
    token = _token(
        auth_client,
        {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"},
    )
    ws, sock = _open(auth_client, token)
    try:
        _until(sock, "ready")
        for i in range(40):  # limit: 30 per 10s
            sock.send_json({"type": "message", "content": f"m{i}"})
        assert "too fast" in _until(sock, "error")["content"]
    finally:
        ws.__exit__(None, None, None)
