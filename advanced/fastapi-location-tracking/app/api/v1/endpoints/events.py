from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import AdminKey, DbSession
from app.schemas.tracking import TRACKER_KEY_PATTERN, GeofenceEventRead
from app.services.geofence_service import GeofenceService

router = APIRouter()

TrackerKey = Annotated[
    str,
    Path(pattern=TRACKER_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[GeofenceEventRead],
    summary="List geofence events for a tracker",
    description="Newest enter/exit events first.",
)
async def list_geofence_events(
    _: AdminKey,
    session: DbSession,
    tracker_key: TrackerKey,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[GeofenceEventRead]:
    return await GeofenceService(session).list_events(tracker_key, limit=limit)
