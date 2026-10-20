import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.deps import (
    get_message_repository,
    get_room_repository,
    get_settings,
    get_user_repository,
    get_ws_hub,
)
from app.core.exceptions import AppError, UnauthorizedError
from app.core.security import decode_token
from app.services.room_service import RoomService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/rooms/{slug}")
async def room_websocket(
    websocket: WebSocket,
    slug: str,
    access_token: str = Query(..., description="JWT access token from POST /auth/login"),
) -> None:
    """Realtime fan-out for a room. REST sends persist; this socket pushes new messages.

    Send the literal text `ping` to receive `pong` (keepalive for proxies).
    """
    await websocket.accept()
    try:
        settings = get_settings()
        users = get_user_repository()
        payload = decode_token(settings=settings, token=access_token, expected_type="access")
        user_id = int(payload["sub"])
        record = users.get_by_id(user_id)
        if record is None or not record.is_active:
            raise UnauthorizedError()
        actor = record.to_read()
    except AppError:
        await websocket.close(code=1008)
        return
    except Exception:
        logger.debug("WebSocket auth failed", exc_info=True)
        await websocket.close(code=1008)
        return

    room_service = RoomService(
        rooms=get_room_repository(),
        messages=get_message_repository(),
        users=users,
    )
    try:
        room_service.require_member_room(actor, slug)
    except AppError:
        await websocket.close(code=1008)
        return

    hub = get_ws_hub()
    await hub.connect(slug, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(slug, websocket)
