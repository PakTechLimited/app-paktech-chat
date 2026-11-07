"""Small helpers shared by the API tests."""

import asyncio

from sqlalchemy import update

from app.db import session as db_session
from app.models.user import User, UserRole

PASSWORD = "s3cret-pass!"


def register(client, name: str) -> dict:
    """Register a user; returns Authorization headers for them."""
    r = client.post(
        "/api/v1/auth/register",
        json={"username": name, "email": f"{name}@example.com", "password": PASSWORD},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def promote(username: str) -> None:
    async def _go():
        async with db_session.AsyncSessionLocal() as db:
            await db.execute(
                update(User)
                .where(User.username == username)
                .values(role=UserRole.admin)
            )
            await db.commit()

    asyncio.run(_go())


def user_id(client, headers) -> int:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]
