from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.device_repository import DeviceRepository
from app.repositories.reading_repository import ReadingRepository
from app.schemas.telemetry import DeviceOverview, DeviceStatus, MetricSeriesPoint, MetricSeriesRead


class MetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._devices = DeviceRepository(session)
        self._readings = ReadingRepository(session)

    async def overview(self, device_key: str) -> DeviceOverview:
        device = await self._devices.get_by_key(device_key)
        if device is None:
            raise NotFoundError("Device", device_key)
        now = datetime.now(UTC)
        since = now - timedelta(hours=1)
        latest = await self._readings.latest_for_device(device.id)
        return DeviceOverview(
            device_key=device.key,
            status=DeviceStatus(device.status),
            total_readings=await self._readings.count_for_device(device.id),
            readings_last_hour=await self._readings.count_since(device.id, since),
            last_seen_at=device.last_seen_at,
            latest_metrics=latest.metrics if latest is not None else None,
        )

    async def metric_series(
        self,
        device_key: str,
        *,
        metric_key: str,
        window_minutes: int,
    ) -> MetricSeriesRead:
        device = await self._devices.get_by_key(device_key)
        if device is None:
            raise NotFoundError("Device", device_key)
        since = datetime.now(UTC) - timedelta(minutes=window_minutes)
        rows = await self._readings.list_since(device.id, since)
        points: list[MetricSeriesPoint] = []
        for row in rows:
            value = row.metrics.get(metric_key)
            if value is None:
                continue
            if isinstance(value, bool):
                numeric = 1.0 if value else 0.0
            elif isinstance(value, (int, float)):
                numeric = float(value)
            else:
                continue
            points.append(MetricSeriesPoint(recorded_at=row.recorded_at, value=numeric))
        return MetricSeriesRead(
            device_key=device_key,
            metric_key=metric_key,
            window_minutes=window_minutes,
            points=points,
        )
