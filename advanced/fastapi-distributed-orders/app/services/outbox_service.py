import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.outbox_repository import OutboxRepository
from app.schemas.outbox import OutboxEventRead
from app.schemas.user import UserRead, UserRole


class OutboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = OutboxRepository(session)

    async def list_events(
        self,
        actor: UserRead,
        *,
        unpublished_only: bool,
    ) -> list[OutboxEventRead]:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only admins can inspect the outbox")
        rows = await self._outbox.list_events(unpublished_only=unpublished_only)
        return [self._to_read(row) for row in rows]

    async def publish(self, actor: UserRead, event_id: int) -> OutboxEventRead:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only admins can ack outbox events")
        event = await self._outbox.get(event_id)
        if event is None:
            raise NotFoundError("OutboxEvent", event_id)
        if event.published_at is not None:
            raise ConflictError("Event was already published")
        await self._outbox.mark_published(event, published_at=datetime.now(UTC))
        await self._session.commit()
        return self._to_read(event)

    @staticmethod
    def _to_read(event) -> OutboxEventRead:
        return OutboxEventRead(
            id=event.id,
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=json.loads(event.payload_json),
            created_at=event.created_at,
            published_at=event.published_at,
        )
