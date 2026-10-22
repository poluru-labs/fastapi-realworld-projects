from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.tracking import (
    TRACKER_KEY_PATTERN,
    GeofenceMonitorAttach,
    GeofenceMonitorRead,
    TrackerCreate,
    TrackerOverview,
    TrackerProvisioned,
    TrackerRead,
)
from app.services.geofence_service import GeofenceService
from app.services.tracker_service import TrackerService

router = APIRouter()

TrackerKey = Annotated[
    str,
    Path(pattern=TRACKER_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[TrackerRead],
    summary="List trackers",
    description="Admin key required. Includes suspended trackers.",
)
async def list_trackers(_: AdminKey, session: DbSession) -> list[TrackerRead]:
    return await TrackerService(session).list_trackers()


@router.post(
    "",
    response_model=TrackerProvisioned,
    status_code=201,
    summary="Provision a tracker",
    description=(
        "Admin key required. Returns a one-time **ingest_token** for the mobile client or "
        "edge gateway. Only a hash is stored server-side."
    ),
)
async def provision_tracker(
    _: AdminKey,
    session: DbSession,
    payload: TrackerCreate,
) -> TrackerProvisioned:
    return await TrackerService(session).provision(payload)


@router.get(
    "/{tracker_key}",
    response_model=TrackerRead,
    summary="Get tracker metadata",
)
async def get_tracker(_: AdminKey, session: DbSession, tracker_key: TrackerKey) -> TrackerRead:
    return await TrackerService(session).get_tracker(tracker_key)


@router.post(
    "/{tracker_key}/suspend",
    response_model=TrackerRead,
    summary="Suspend location ingest",
)
async def suspend_tracker(
    _: AdminKey, session: DbSession, tracker_key: TrackerKey
) -> TrackerRead:
    return await TrackerService(session).suspend(tracker_key)


@router.post(
    "/{tracker_key}/resume",
    response_model=TrackerRead,
    summary="Resume an active tracker",
)
async def resume_tracker(_: AdminKey, session: DbSession, tracker_key: TrackerKey) -> TrackerRead:
    return await TrackerService(session).resume(tracker_key)


@router.get(
    "/{tracker_key}/overview",
    response_model=TrackerOverview,
    summary="Tracker dashboard snapshot",
    description="Ping counts, last position, and number of monitored geofences.",
)
async def tracker_overview(
    _: AdminKey, session: DbSession, tracker_key: TrackerKey
) -> TrackerOverview:
    return await TrackerService(session).overview(tracker_key)


@router.post(
    "/{tracker_key}/monitors",
    response_model=GeofenceMonitorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a geofence monitor",
    description="Links a tracker to a geofence for enter/exit detection on ingest.",
)
async def attach_geofence_monitor(
    _: AdminKey,
    session: DbSession,
    tracker_key: TrackerKey,
    payload: GeofenceMonitorAttach,
) -> GeofenceMonitorRead:
    return await GeofenceService(session).attach_monitor(tracker_key, payload.geofence_id)
