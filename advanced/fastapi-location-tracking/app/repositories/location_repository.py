from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking import LocationIdempotencyRecord, LocationPing


class LocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_ping(self, ping: LocationPing) -> LocationPing:
        self._session.add(ping)
        await self._session.flush()
        return ping

    async def dedupe_exists(self, tracker_id: int, dedupe_key: str) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(LocationPing)
            .where(LocationPing.tracker_id == tracker_id, LocationPing.dedupe_key == dedupe_key)
        )
        return int(result or 0) > 0

    async def count_for_tracker(self, tracker_id: int) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(LocationPing)
            .where(LocationPing.tracker_id == tracker_id)
        )
        return int(result or 0)

    async def count_since(self, tracker_id: int, since: datetime) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(LocationPing)
            .where(LocationPing.tracker_id == tracker_id, LocationPing.recorded_at >= since)
        )
        return int(result or 0)

    async def list_since(self, tracker_id: int, since: datetime) -> list[LocationPing]:
        result = await self._session.scalars(
            select(LocationPing)
            .where(LocationPing.tracker_id == tracker_id, LocationPing.recorded_at >= since)
            .order_by(LocationPing.recorded_at)
        )
        return list(result)

    async def get_idempotency(self, tracker_id: int, key: str) -> LocationIdempotencyRecord | None:
        return await self._session.scalar(
            select(LocationIdempotencyRecord).where(
                LocationIdempotencyRecord.tracker_id == tracker_id,
                LocationIdempotencyRecord.idempotency_key == key,
            )
        )

    async def add_idempotency(self, record: LocationIdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()
