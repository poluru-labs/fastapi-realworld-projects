from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from app.api.deps import CurrentUser, DbSession, IdempotencyKey
from app.schemas.chat import MessageCreate, MessageRead
from app.services.message_service import MessageService

router = APIRouter(prefix="/rooms/{slug}/messages", tags=["messages"])

_SEND_EXAMPLES = {
    "status_update": {
        "summary": "Short room message",
        "value": {"body": "Deploy finished — please verify dashboards."},
    }
}


@router.get(
    "",
    response_model=list[MessageRead],
    summary="List messages after a sequence cursor",
    description=(
        "Members only. Pass **after_sequence** from your last sync (0 for the beginning). "
        "Messages are ordered by monotonic **sequence** per room."
    ),
)
async def list_messages(
    slug: str,
    session: DbSession,
    user: CurrentUser,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[MessageRead]:
    return await MessageService(session).list_messages(
        user,
        slug,
        after_sequence=after_sequence,
        limit=limit,
    )


@router.post(
    "",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message (idempotent)",
    description=(
        "Requires **Idempotency-Key** so mobile or multi-region clients can retry safely. "
        "Each send enqueues **delivery outbox** rows for other members; edge **relays** "
        "claim and complete those deliveries with a lease."
    ),
)
async def send_message(
    slug: str,
    session: DbSession,
    user: CurrentUser,
    idempotency_key: IdempotencyKey,
    payload: Annotated[MessageCreate, Body(openapi_examples=_SEND_EXAMPLES)],
) -> MessageRead:
    return await MessageService(session).send(
        user,
        slug,
        payload,
        idempotency_key=idempotency_key,
    )
