"""Idempotent seed data. Safe to run from several workers at once."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import session as db_session
from app.models.room import Room

logger = logging.getLogger(__name__)

# Order matters on a fresh DB: ids 1, 2, 3 (the legacy UI hardcodes these).
DEFAULT_ROOMS = [
    ("general", "Team-wide announcements and chat"),
    ("engineering", "Tech discussions"),
    ("random", "Everything else"),
]


async def seed_default_rooms() -> None:
    async with db_session.AsyncSessionLocal() as db:
        for name, description in DEFAULT_ROOMS:
            exists = await db.execute(select(Room.id).where(Room.name == name))
            if exists.scalar_one_or_none() is not None:
                continue
            db.add(Room(name=name, description=description))
            try:
                await db.commit()
                logger.info("Seeded room #%s", name)
            except IntegrityError:
                # Another worker inserted it first; that's fine.
                await db.rollback()
