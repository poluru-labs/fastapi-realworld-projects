import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WsHub:
    """In-process fan-out. Production would use Redis pub/sub or similar."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, room_slug: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(room_slug, set()).add(websocket)

    async def disconnect(self, room_slug: str, websocket: WebSocket) -> None:
        async with self._lock:
            peers = self._rooms.get(room_slug)
            if peers is None:
                return
            peers.discard(websocket)
            if not peers:
                self._rooms.pop(room_slug, None)

    async def broadcast(self, room_slug: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            peers = list(self._rooms.get(room_slug, set()))
        for websocket in peers:
            try:
                await websocket.send_json(payload)
            except Exception:
                logger.debug("Dropping websocket client for room %s", room_slug, exc_info=True)
