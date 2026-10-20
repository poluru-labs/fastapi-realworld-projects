from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import TelemetryIdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, device_id: int, key: str) -> TelemetryIdempotencyRecord | None:
        return await self._session.scalar(
            select(TelemetryIdempotencyRecord).where(
                TelemetryIdempotencyRecord.device_id == device_id,
                TelemetryIdempotencyRecord.idempotency_key == key,
            )
        )

    async def add(self, record: TelemetryIdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()
