import asyncio
import json
import logging

from fastapi import WebSocket

from app.services.redis_service import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections per room.

    Fan-out strategy:
    - Local delivery: push directly to WebSocket connections on THIS pod.
    - Cross-pod delivery: subscribe to Redis Pub/Sub channel per room.
      Any pod that receives a message publishes to Redis; all pods
      subscribed to that channel deliver it to their local connections.
    """

    def __init__(self) -> None:
        # room_id -> {username -> WebSocket}
        self._connections: dict[int, dict[str, WebSocket]] = {}
        self._pubsub_tasks: dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, room_id: int, username: str) -> None:
        await websocket.accept()
        if room_id not in self._connections:
            self._connections[room_id] = {}
            await self._start_pubsub_listener(room_id)
        self._connections[room_id][username] = websocket
        logger.info("WS connected: user=%s room=%d", username, room_id)

    async def disconnect(self, room_id: int, username: str) -> None:
        if room_id in self._connections:
            self._connections[room_id].pop(username, None)
            if not self._connections[room_id]:
                del self._connections[room_id]
                await self._stop_pubsub_listener(room_id)
        logger.info("WS disconnected: user=%s room=%d", username, room_id)

    async def broadcast_local(self, room_id: int, event: dict) -> None:
        if room_id not in self._connections:
            return
        dead = []
        for username, ws in self._connections[room_id].items():
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(username)
        for u in dead:
            await self.disconnect(room_id, u)

    def active_connections_count(self) -> int:
        return sum(len(v) for v in self._connections.values())

    async def _start_pubsub_listener(self, room_id: int) -> None:
        client = await get_redis()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"room:{room_id}")

        async def _listen() -> None:
            try:
                async for raw in pubsub.listen():
                    if raw["type"] != "message":
                        continue
                    try:
                        event = json.loads(raw["data"])
                        await self.broadcast_local(room_id, event)
                    except (json.JSONDecodeError, Exception) as exc:
                        logger.warning("Pub/Sub decode error: %s", exc)
            except asyncio.CancelledError:
                pass
            finally:
                await pubsub.unsubscribe(f"room:{room_id}")
                await pubsub.aclose()

        self._pubsub_tasks[room_id] = asyncio.create_task(_listen())

    async def _stop_pubsub_listener(self, room_id: int) -> None:
        task = self._pubsub_tasks.pop(room_id, None)
        if task:
            task.cancel()


manager = ConnectionManager()
