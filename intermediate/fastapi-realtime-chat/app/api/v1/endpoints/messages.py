from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_current_user, get_message_service
from app.schemas.chat import SLUG_PATTERN, MessageCreate, MessagePage, MessageRead
from app.schemas.user import UserRead
from app.services.message_service import MessageService

router = APIRouter()

Slug = Annotated[
    str,
    Path(pattern=SLUG_PATTERN.pattern, min_length=2, max_length=64, examples=["general"]),
]


@router.get(
    "",
    response_model=MessagePage,
    summary="Message history after a sequence",
    description=(
        "Members only. Pass `after_sequence` from your last sync (0 for the beginning). "
        "Use with the room WebSocket for live delivery."
    ),
)
def list_messages(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MessageService, Depends(get_message_service)],
    after_sequence: Annotated[
        int,
        Query(ge=0, description="Return messages with sequence strictly greater than this."),
    ] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MessagePage:
    return service.list_messages(actor, slug, after_sequence=after_sequence, limit=limit)


@router.post(
    "",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description=(
        "Persists the message, bumps the room sequence, and pushes a `message` event "
        "to every WebSocket connected on this room."
    ),
)
async def send_message(
    slug: Slug,
    payload: MessageCreate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MessageService, Depends(get_message_service)],
) -> MessageRead:
    return await service.send(actor, slug, payload)
