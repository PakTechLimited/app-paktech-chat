import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.room import Room
from app.schemas.room import RoomCreate, RoomOut

router = APIRouter(prefix="/rooms", tags=["rooms"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[RoomOut])
async def list_rooms(db: AsyncSession = Depends(get_db)) -> list[Room]:
    result = await db.execute(select(Room).order_by(Room.name))
    return list(result.scalars().all())


@router.post("/", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db)) -> Room:
    existing = await db.execute(select(Room).where(Room.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room '{payload.name}' already exists.",
        )
    room = Room(name=payload.name, description=payload.description)
    db.add(room)
    await db.flush()
    await db.refresh(room)
    logger.info("Room created: %s", room.name)
    return room


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)) -> Room:
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found."
        )
    return room
