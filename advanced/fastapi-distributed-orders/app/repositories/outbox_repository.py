from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> OutboxEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_events(self, *, unpublished_only: bool) -> list[OutboxEvent]:
        query = select(OutboxEvent).order_by(OutboxEvent.created_at)
        if unpublished_only:
            query = query.where(OutboxEvent.published_at.is_(None))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get(self, event_id: int) -> OutboxEvent | None:
        return await self._session.get(OutboxEvent, event_id)

    async def mark_published(self, event: OutboxEvent, *, published_at: datetime) -> None:
        event.published_at = published_at
        await self._session.flush()
