from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import AdminKey, DbSession
from app.schemas.telemetry import DEVICE_KEY_PATTERN, DeviceOverview, MetricSeriesRead
from app.services.metrics_service import MetricsService

router = APIRouter()

DeviceKey = Annotated[
    str,
    Path(pattern=DEVICE_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "/overview",
    response_model=DeviceOverview,
    summary="Device health snapshot",
    description="Admin key required. Uses `recorded_at` for hourly counts.",
)
async def device_overview(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
) -> DeviceOverview:
    return await MetricsService(session).overview(device_key)


@router.get(
    "/series",
    response_model=MetricSeriesRead,
    summary="Metric time series",
    description="Admin key required. Numeric and boolean metrics are plotted; strings are skipped.",
)
async def metric_series(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
    metric_key: Annotated[str, Query(min_length=1, max_length=64, examples=["temp_c"])],
    window_minutes: Annotated[int, Query(ge=1, le=1440)] = 60,
) -> MetricSeriesRead:
    return await MetricsService(session).metric_series(
        device_key,
        metric_key=metric_key,
        window_minutes=window_minutes,
    )
