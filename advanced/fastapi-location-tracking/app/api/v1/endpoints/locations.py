from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminKey, DbSession, IdempotencyKey, TrackerToken
from app.schemas.tracking import (
    TRACKER_KEY_PATTERN,
    LocationIngest,
    LocationIngestResult,
    LocationTrail,
)
from app.services.location_service import LocationService

router = APIRouter()

TrackerKey = Annotated[
    str,
    Path(pattern=TRACKER_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.post(
    "",
    response_model=LocationIngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a GPS ping",
    description=(
        "**X-Tracker-Token** and **Idempotency-Key** are required. "
        "Each accepted ping updates the tracker’s last position and evaluates "
        "circular geofences assigned via monitors. Enter/exit transitions appear "
        "in `geofence_events`."
    ),
)
async def ingest_location(
    session: DbSession,
    tracker_key: TrackerKey,
    payload: LocationIngest,
    ingest_token: TrackerToken,
    idempotency_key: IdempotencyKey,
) -> LocationIngestResult:
    return await LocationService(session).ingest(
        tracker_key,
        ingest_token,
        idempotency_key,
        payload,
    )


@router.get(
    "/trail",
    response_model=LocationTrail,
    summary="Recent location trail",
    description="Admin key required. Returns pings with `recorded_at` within the window.",
)
async def location_trail(
    _: AdminKey,
    session: DbSession,
    tracker_key: TrackerKey,
    window_minutes: Annotated[int, Query(ge=1, le=10_080)] = 60,
) -> LocationTrail:
    return await LocationService(session).trail(tracker_key, window_minutes=window_minutes)
