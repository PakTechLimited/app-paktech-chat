"""Refresh-cookie flow: httpOnly cookie, rotation, replay detection, logout.

Runs without Postgres/Redis: in-memory SQLite + fakeredis.
"""

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import auth
from app.db.session import Base, get_db
from app.services import redis_service

CREDS = {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"}


@pytest.fixture
def client(monkeypatch):
    import asyncio

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    async def _get_db():
        async with Session() as session:
            yield session
            await session.commit()

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _get_redis():
        return fake

    monkeypatch.setattr(redis_service, "get_redis", _get_redis)
    monkeypatch.setattr("app.services.token_store.get_redis", _get_redis)

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app, base_url="http://localhost") as c:
        yield c


def _register(client):
    r = client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 201
    return r


def test_login_sets_httponly_cookie_and_hides_refresh_from_body(client):
    r = _register(client)
    assert "refresh_token" not in r.json()
    set_cookie = r.headers["set-cookie"].lower()
    assert "pt_refresh=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie


def test_refresh_rotates_and_old_token_is_dead(client):
    _register(client)
    old = client.cookies.get("pt_refresh", path="/api/v1/auth")
    assert old

    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    new = client.cookies.get("pt_refresh", path="/api/v1/auth")
    assert new and new != old

    # Replaying the OLD token must fail ...
    client.cookies.clear()
    client.cookies.set("pt_refresh", old, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401

    # ... and reuse detection revoked the new one too (all sessions killed).
    client.cookies.clear()
    client.cookies.set("pt_refresh", new, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_without_cookie_is_401(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_token_and_clears_cookie(client):
    _register(client)
    tok = client.cookies.get("pt_refresh", path="/api/v1/auth")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.clear()
    client.cookies.set("pt_refresh", tok, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401
