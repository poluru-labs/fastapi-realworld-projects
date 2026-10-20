from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import IngestIdempotencyRecord


class IngestIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, stream_id: int, key: str) -> IngestIdempotencyRecord | None:
        return await self._session.scalar(
            select(IngestIdempotencyRecord).where(
                IngestIdempotencyRecord.stream_id == stream_id,
                IngestIdempotencyRecord.idempotency_key == key,
            )
        )

    async def add(self, record: IngestIdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()
