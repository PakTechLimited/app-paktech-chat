import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.schemas.websocket import WSEventType
from app.services.connection_manager import manager
from app.services.redis_service import publish_message

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    username: str = Query(...),
) -> None:
    """
    WebSocket endpoint: ws://host/ws/{room_id}?username=alice

    Message protocol (JSON):
      Client → Server: {"type": "message", "content": "hello"}
                       {"type": "typing"}
                       {"type": "typing_stop"}
      Server → Client: {"type": "message", "room_id": 1,
                        "username": "alice", "content": "hello",
                        "timestamp": "2025-01-01T10:00:00Z"}
    """
    await manager.connect(websocket, room_id, username)

    join_event = {
        "type": WSEventType.USER_JOINED,
        "room_id": room_id,
        "username": username,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await publish_message(room_id, join_event)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": WSEventType.ERROR, "content": "Invalid JSON"})
                )
                continue

            msg_type = data.get("type", "message")

            if msg_type == "typing" or msg_type == "typing_stop":
                event = {
                    "type": msg_type,
                    "room_id": room_id,
                    "username": username,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await publish_message(room_id, event)

            elif msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue
                event = {
                    "type": WSEventType.MESSAGE,
                    "room_id": room_id,
                    "username": username,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await publish_message(room_id, event)

    except WebSocketDisconnect:
        await manager.disconnect(room_id, username)
        leave_event = {
            "type": WSEventType.USER_LEFT,
            "room_id": room_id,
            "username": username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await publish_message(room_id, leave_event)
        logger.info("User %s left room %d", username, room_id)
