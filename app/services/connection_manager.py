import asyncio
import json
import logging

from fastapi import WebSocket

from app.services.redis_service import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections per room.

    Connections are keyed by the socket itself (not the username), so a user can
    have several tabs open and one tab closing never breaks another.

    Fan-out strategy:
    - Local delivery: push directly to WebSocket connections on THIS pod.
    - Cross-pod delivery: subscribe to Redis Pub/Sub channel per room.
      Any pod that receives a message publishes to Redis; all pods
      subscribed to that channel deliver it to their local connections.
    """

    def __init__(self) -> None:
        # room_id -> {websocket -> username}
        self._connections: dict[int, dict[WebSocket, str]] = {}
        self._pubsub_tasks: dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, room_id: int, username: str) -> bool:
        """Register an ACCEPTED, authenticated socket.

        Returns True if this is the user's first connection in the room
        (so callers announce "joined" once, not once per tab).
        """
        if room_id not in self._connections:
            self._connections[room_id] = {}
            await self._start_pubsub_listener(room_id)
        first = username not in self._connections[room_id].values()
        self._connections[room_id][websocket] = username
        logger.info("WS connected: user=%s room=%d", username, room_id)
        return first

    async def disconnect(self, room_id: int, websocket: WebSocket) -> tuple[str, bool]:
        """Remove a socket. Returns (username, was_last_connection_for_user)."""
        room = self._connections.get(room_id, {})
        username = room.pop(websocket, "")
        last = bool(username) and username not in room.values()
        if room_id in self._connections and not self._connections[room_id]:
            del self._connections[room_id]
            await self._stop_pubsub_listener(room_id)
        logger.info("WS disconnected: user=%s room=%d", username, room_id)
        return username, last

    def online_users(self, room_id: int) -> list[str]:
        return sorted(set(self._connections.get(room_id, {}).values()))

    async def broadcast_local(self, room_id: int, event: dict) -> None:
        room = self._connections.get(room_id)
        if not room:
            return
        payload = json.dumps(event)
        dead = []
        for ws in list(room):
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001 - a broken socket must not stop fan-out
                dead.append(ws)
        for ws in dead:
            await self.disconnect(room_id, ws)

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
