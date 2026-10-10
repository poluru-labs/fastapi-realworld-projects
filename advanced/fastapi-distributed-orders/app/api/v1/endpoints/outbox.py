from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.schemas.outbox import OutboxEventRead
from app.services.outbox_service import OutboxService

router = APIRouter(prefix="/outbox", tags=["outbox"])


@router.get(
    "",
    response_model=list[OutboxEventRead],
    summary="Inspect outbox events (admin)",
    description=(
        "Transactional outbox table for downstream consumers. "
        "Filter `unpublished_only=true` to simulate a relay worker backlog."
    ),
)
async def list_outbox(
    actor: AdminUser,
    session: DbSession,
    unpublished_only: bool = Query(default=True),
) -> list[OutboxEventRead]:
    return await OutboxService(session).list_events(actor, unpublished_only=unpublished_only)


@router.post(
    "/{event_id}/publish",
    response_model=OutboxEventRead,
    summary="Acknowledge delivery (admin)",
    description="Sets `published_at` — stand-in for a message broker ack.",
)
async def publish_outbox_event(
    event_id: int,
    actor: AdminUser,
    session: DbSession,
) -> OutboxEventRead:
    return await OutboxService(session).publish(actor, event_id)
