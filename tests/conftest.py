"""Shared fixtures: auth router on in-memory SQLite + fakeredis (no Postgres/Redis)."""

import asyncio

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import ai, auth, messages, rooms, websocket
from app.db import session as db_session
from app.db.seed import seed_default_rooms
from app.db.session import Base, get_db
from app.services import redis_service
from app.services.connection_manager import manager


@pytest.fixture
def auth_client(monkeypatch):
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
    monkeypatch.setattr("app.core.rate_limit.get_redis", _get_redis)
    monkeypatch.setattr("app.services.connection_manager.get_redis", _get_redis)
    # WebSocket handler opens its own sessions via this factory
    monkeypatch.setattr(db_session, "AsyncSessionLocal", Session)
    manager._connections.clear()
    manager._pubsub_tasks.clear()
    asyncio.run(seed_default_rooms())

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")
    app.include_router(rooms.router, prefix="/api/v1")
    app.include_router(messages.router, prefix="/api/v1")
    app.include_router(websocket.router)
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app, base_url="http://localhost") as c:
        yield c
