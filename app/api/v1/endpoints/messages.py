import logging
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.message import Message
from app.models.room import Room
from app.schemas.message import MessageCreate, MessageOut
from app.schemas.websocket import WSEventType
from app.services.connection_manager import manager
from app.services.redis_service import publish_message

router = APIRouter(prefix="/messages", tags=["messages"])
logger = logging.getLogger(__name__)


@router.get("/{room_id}", response_model=list[MessageOut])
async def get_room_messages(
    room_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.author))
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return [
        MessageOut(
            id=m.id,
            content=m.content,
            room_id=m.room_id,
            author_id=m.author_id,
            author_username=m.author.username if m.author else None,
            created_at=m.created_at,
        )
        for m in reversed(messages)
    ]


@router.post("/", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def post_message(
    payload: MessageCreate,
    author_id: int = Query(
        ..., description="Temporary: pass user ID until auth is wired"
    ),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    room_result = await db.execute(select(Room).where(Room.id == payload.room_id))
    if not room_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found."
        )

    msg = Message(content=payload.content, room_id=payload.room_id, author_id=author_id)
    db.add(msg)
    await db.flush()
    await db.refresh(msg, ["author"])

    event = {
        "type": WSEventType.MESSAGE,
        "room_id": msg.room_id,
        "username": msg.author.username if msg.author else str(author_id),
        "content": msg.content,
        "timestamp": msg.created_at.replace(tzinfo=timezone.utc).isoformat(),
    }
    await publish_message(msg.room_id, event)

    return MessageOut(
        id=msg.id,
        content=msg.content,
        room_id=msg.room_id,
        author_id=msg.author_id,
        author_username=msg.author.username if msg.author else None,
        created_at=msg.created_at,
    )
