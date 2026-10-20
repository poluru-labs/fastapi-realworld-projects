from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsEvent


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AnalyticsEvent) -> AnalyticsEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def dedupe_exists(self, stream_id: int, dedupe_key: str) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.stream_id == stream_id,
                AnalyticsEvent.dedupe_key == dedupe_key,
            )
        )
        return int(result or 0) > 0

    async def count_for_stream(self, stream_id: int) -> int:
        result = await self._session.scalar(
            select(func.count()).select_from(AnalyticsEvent).where(
                AnalyticsEvent.stream_id == stream_id
            )
        )
        return int(result or 0)

    async def count_since(self, stream_id: int, since: datetime) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.stream_id == stream_id,
                AnalyticsEvent.occurred_at >= since,
            )
        )
        return int(result or 0)

    async def list_since(self, stream_id: int, since: datetime) -> list[AnalyticsEvent]:
        result = await self._session.scalars(
            select(AnalyticsEvent)
            .where(
                AnalyticsEvent.stream_id == stream_id,
                AnalyticsEvent.occurred_at >= since,
            )
            .order_by(AnalyticsEvent.occurred_at)
        )
        return list(result)

    async def top_event_names_since(
        self,
        stream_id: int,
        since: datetime,
        *,
        limit: int,
    ) -> list[tuple[str, int]]:
        rows = await self._session.execute(
            select(AnalyticsEvent.event_name, func.count())
            .where(
                AnalyticsEvent.stream_id == stream_id,
                AnalyticsEvent.occurred_at >= since,
            )
            .group_by(AnalyticsEvent.event_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(name, int(count)) for name, count in rows.all()]

    async def distinct_event_names_since(self, stream_id: int, since: datetime) -> int:
        result = await self._session.scalar(
            select(func.count(func.distinct(AnalyticsEvent.event_name))).where(
                AnalyticsEvent.stream_id == stream_id,
                AnalyticsEvent.occurred_at >= since,
            )
        )
        return int(result or 0)
