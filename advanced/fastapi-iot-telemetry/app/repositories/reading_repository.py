from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import TelemetryReading


class ReadingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, reading: TelemetryReading) -> TelemetryReading:
        self._session.add(reading)
        await self._session.flush()
        return reading

    async def dedupe_exists(self, device_id: int, dedupe_key: str) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(TelemetryReading)
            .where(
                TelemetryReading.device_id == device_id,
                TelemetryReading.dedupe_key == dedupe_key,
            )
        )
        return int(result or 0) > 0

    async def count_for_device(self, device_id: int) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(TelemetryReading)
            .where(TelemetryReading.device_id == device_id)
        )
        return int(result or 0)

    async def count_since(self, device_id: int, since: datetime) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(TelemetryReading)
            .where(
                TelemetryReading.device_id == device_id,
                TelemetryReading.recorded_at >= since,
            )
        )
        return int(result or 0)

    async def latest_for_device(self, device_id: int) -> TelemetryReading | None:
        return await self._session.scalar(
            select(TelemetryReading)
            .where(TelemetryReading.device_id == device_id)
            .order_by(TelemetryReading.recorded_at.desc(), TelemetryReading.id.desc())
            .limit(1)
        )

    async def list_since(self, device_id: int, since: datetime) -> list[TelemetryReading]:
        result = await self._session.scalars(
            select(TelemetryReading)
            .where(
                TelemetryReading.device_id == device_id,
                TelemetryReading.recorded_at >= since,
            )
            .order_by(TelemetryReading.recorded_at)
        )
        return list(result)
