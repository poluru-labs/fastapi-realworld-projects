from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.event_repository import EventRepository
from app.repositories.stream_repository import StreamRepository
from app.schemas.analytics import MetricsOverview, TimeSeriesBucket, TimeSeriesRead
from app.services.stream_service import StreamService


class MetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._streams = StreamRepository(session)
        self._events = EventRepository(session)
        self._stream_service = StreamService(session)

    async def overview(self, stream_key: str) -> MetricsOverview:
        stream_read = await self._stream_service.get_stream(stream_key)
        row = await self._streams.get_by_key(stream_key)
        assert row is not None
        now = datetime.now(UTC)
        since = now - timedelta(minutes=15)
        total = await self._events.count_for_stream(row.id)
        recent = await self._events.count_since(row.id, since)
        distinct = await self._events.distinct_event_names_since(row.id, since)
        top = await self._events.top_event_names_since(row.id, since, limit=5)
        return MetricsOverview(
            stream_key=stream_read.key,
            total_events=total,
            events_last_15m=recent,
            distinct_event_names_last_15m=distinct,
            top_event_names_last_15m=top,
        )

    async def time_series(
        self,
        stream_key: str,
        *,
        window_minutes: int,
        bucket_seconds: int,
    ) -> TimeSeriesRead:
        row = await self._streams.get_by_key(stream_key)
        if row is None:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Stream", stream_key)
        now = datetime.now(UTC)
        since = now - timedelta(minutes=window_minutes)
        events = await self._events.list_since(row.id, since)
        buckets = _bucket_counts(events, since=since, bucket_seconds=bucket_seconds, until=now)
        return TimeSeriesRead(
            stream_key=stream_key,
            window_minutes=window_minutes,
            bucket_seconds=bucket_seconds,
            buckets=buckets,
        )


def _bucket_counts(
    events,
    *,
    since: datetime,
    bucket_seconds: int,
    until: datetime,
) -> list[TimeSeriesBucket]:
    """Roll up in Python so SQLite and Postgres share the same teaching path."""
    if bucket_seconds < 1:
        bucket_seconds = 60
    start = int(since.timestamp())
    end = int(until.timestamp())
    counts: dict[int, int] = {}
    cursor = start - (start % bucket_seconds)
    while cursor <= end:
        counts[cursor] = 0
        cursor += bucket_seconds

    for event in events:
        ts = int(event.occurred_at.timestamp())
        bucket = ts - (ts % bucket_seconds)
        if bucket in counts:
            counts[bucket] += 1

    return [
        TimeSeriesBucket(
            bucket_start=datetime.fromtimestamp(ts, tz=UTC),
            count=count,
        )
        for ts, count in sorted(counts.items())
    ]
