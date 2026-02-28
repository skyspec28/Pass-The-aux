import json
import uuid
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()

CHANNEL_PREFIX = "session:"


class ConnectionManager:
    """
    Manages WebSocket connections grouped by session_id.

    Broadcasting strategy:
    - broadcast() publishes to Redis pub/sub channel `session:{session_id}`.
    - A background listener task (started in main.py lifespan) subscribes to
      `session:*` and calls broadcast_local() to deliver messages to in-process
      WebSocket connections.
    - This decouples ARQ worker broadcasts (which publish to Redis) from
      in-process WS delivery, enabling multi-process correctness.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._redis: Any = None  # set during app startup

    def set_redis(self, redis: Any) -> None:
        self._redis = redis

    async def connect(self, session_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        key = str(session_id)
        self._rooms.setdefault(key, set()).add(websocket)
        logger.info("ws.connected", session_id=key, total=len(self._rooms[key]))

    def disconnect(self, session_id: uuid.UUID, websocket: WebSocket) -> None:
        key = str(session_id)
        room = self._rooms.get(key, set())
        room.discard(websocket)
        if not room:
            self._rooms.pop(key, None)
        logger.info("ws.disconnected", session_id=key)

    async def broadcast_local(self, session_id_str: str, message: str) -> None:
        """Deliver a raw JSON string to all WS clients in this process."""
        room = self._rooms.get(session_id_str, set())
        dead: set[WebSocket] = set()
        for ws in list(room):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            room.discard(ws)

    async def broadcast(self, session_id: uuid.UUID, event_type: str, data: dict[str, Any]) -> None:
        """Publish event to Redis pub/sub; the listener loop calls broadcast_local."""
        message = json.dumps({"type": event_type, "data": data})
        if self._redis is not None:
            await self._redis.publish(f"{CHANNEL_PREFIX}{session_id}", message)
        else:
            # Fallback for tests (no Redis)
            await self.broadcast_local(str(session_id), message)


manager = ConnectionManager()

