import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.v1.dependencies import user_from_access_token
from app.core.config import settings
from app.core.rate_limit import enforce
from app.db import session as db_session
from app.models.message import Message
from app.models.room import Room
from app.models.user import User
from app.schemas.websocket import WSEventType
from app.services.connection_manager import manager
from app.services.redis_service import publish_message

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)

AUTH_TIMEOUT_SECONDS = 5
MAX_MESSAGE_LENGTH = 4000

# Close codes (4000-4999 are application-defined)
CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN_ORIGIN = 4403
CLOSE_NO_SUCH_ROOM = 4404


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(dt: datetime) -> str:
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


async def _authenticate(websocket: WebSocket) -> User | None:
    """First-message handshake: {"type":"auth","token":"<access token>"}.

    The token is sent in the first frame, not the URL, so it never lands in
    proxy/access logs or browser history.
    """
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT_SECONDS)
        data = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        return None
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or data.get("type") != "auth":
        return None
    async with db_session.AsyncSessionLocal() as db:
        return await user_from_access_token(token, db)


async def _close(websocket: WebSocket, code: int) -> None:
    """Close, ignoring sockets the client already dropped."""
    try:
        await websocket.close(code=code)
    except RuntimeError:
        pass


async def _send_error(websocket: WebSocket, content: str) -> None:
    await websocket.send_text(
        json.dumps({"type": WSEventType.ERROR, "content": content})
    )


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int) -> None:
    """
    WebSocket endpoint: ws://host/ws/{room_id}

    1. Client connects, then within 5s sends {"type":"auth","token":"<access>"}.
    2. Server replies {"type":"ready","username":...} or closes with 4401.
    3. Client → Server: {"type":"message","content":"hi"} | {"type":"typing"}
                        | {"type":"typing_stop"}
    4. Server → Client: events with the username taken from the verified account,
       never from client input. Messages are persisted before they are broadcast.
    """
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        await _close(websocket, CLOSE_FORBIDDEN_ORIGIN)
        return

    await websocket.accept()
    user = await _authenticate(websocket)
    if user is None:
        await _close(websocket, CLOSE_UNAUTHORIZED)
        return

    async with db_session.AsyncSessionLocal() as db:
        room = (
            await db.execute(select(Room).where(Room.id == room_id))
        ).scalar_one_or_none()
    if room is None:
        await _close(websocket, CLOSE_NO_SUCH_ROOM)
        return

    first_tab = await manager.connect(websocket, room_id, user.username)
    await websocket.send_text(
        json.dumps({"type": WSEventType.READY, "username": user.username})
    )
    if first_tab:
        await publish_message(
            room_id,
            {
                "type": WSEventType.USER_JOINED,
                "room_id": room_id,
                "username": user.username,
                "timestamp": _now(),
            },
        )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON")
                continue
            if not isinstance(data, dict):
                await _send_error(websocket, "Invalid message")
                continue

            msg_type = data.get("type", "message")

            if msg_type in ("typing", "typing_stop"):
                try:
                    await enforce(f"ws-typing:{user.id}", limit=60, window_seconds=10)
                except HTTPException:
                    continue  # silently drop typing floods
                await publish_message(
                    room_id,
                    {
                        "type": msg_type,
                        "room_id": room_id,
                        "username": user.username,
                        "timestamp": _now(),
                    },
                )

            elif msg_type == "message":
                content = str(data.get("content", "")).strip()
                if not content:
                    continue
                if len(content) > MAX_MESSAGE_LENGTH:
                    await _send_error(
                        websocket, f"Message too long (max {MAX_MESSAGE_LENGTH})."
                    )
                    continue
                try:
                    await enforce(f"ws-msg:{user.id}", limit=30, window_seconds=10)
                except HTTPException:
                    await _send_error(websocket, "You are sending messages too fast.")
                    continue

                async with db_session.AsyncSessionLocal() as db:
                    msg = Message(content=content, room_id=room_id, author_id=user.id)
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)
                await publish_message(
                    room_id,
                    {
                        "type": WSEventType.MESSAGE,
                        "id": msg.id,
                        "room_id": room_id,
                        "username": user.username,
                        "avatar_color": user.avatar_color,
                        "content": msg.content,
                        "timestamp": _iso(msg.created_at),
                    },
                )

    except WebSocketDisconnect:
        pass
    finally:
        username, last_tab = await manager.disconnect(room_id, websocket)
        if last_tab:
            await publish_message(
                room_id,
                {
                    "type": WSEventType.USER_LEFT,
                    "room_id": room_id,
                    "username": username,
                    "timestamp": _now(),
                },
            )
        logger.info("User %s left room %d", username, room_id)
