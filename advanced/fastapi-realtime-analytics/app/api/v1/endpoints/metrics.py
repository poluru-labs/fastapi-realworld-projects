from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import AdminKey, DbSession
from app.schemas.analytics import STREAM_KEY_PATTERN, MetricsOverview, TimeSeriesRead
from app.services.metrics_service import MetricsService

router = APIRouter()

StreamKey = Annotated[
    str,
    Path(pattern=STREAM_KEY_PATTERN.pattern, min_length=1, max_length=64),
]


@router.get(
    "/overview",
    response_model=MetricsOverview,
    summary="Rolling overview",
    description=(
        "Admin key required. Counts include seed data after migrate/seed. "
        "The 15-minute window uses each event's `occurred_at`, not ingest time."
    ),
)
async def metrics_overview(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
) -> MetricsOverview:
    return await MetricsService(session).overview(stream_key)


@router.get(
    "/time-series",
    response_model=TimeSeriesRead,
    summary="Bucketed event volume",
    description=(
        "Admin key required. Buckets are computed in the service layer so SQLite "
        "and Postgres behave the same in tests."
    ),
)
async def metrics_time_series(
    _: AdminKey,
    session: DbSession,
    stream_key: StreamKey,
    window_minutes: Annotated[int, Query(ge=1, le=1440, description="Lookback window.")] = 60,
    bucket_seconds: Annotated[
        int,
        Query(ge=60, le=3600, description="Bucket width in seconds."),
    ] = 60,
) -> TimeSeriesRead:
    return await MetricsService(session).time_series(
        stream_key,
        window_minutes=window_minutes,
        bucket_seconds=bucket_seconds,
    )
