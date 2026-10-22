from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.tracking import GeofenceCreate, GeofenceRead
from app.services.geofence_service import GeofenceService

router = APIRouter()
GeofenceId = Annotated[int, Path(ge=1)]


@router.get(
    "",
    response_model=list[GeofenceRead],
    summary="List geofences",
)
async def list_geofences(_: AdminKey, session: DbSession) -> list[GeofenceRead]:
    return await GeofenceService(session).list_geofences()


@router.post(
    "",
    response_model=GeofenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a circular geofence",
    description="Center point plus radius in meters. Names must be unique.",
)
async def create_geofence(
    _: AdminKey,
    session: DbSession,
    payload: GeofenceCreate,
) -> GeofenceRead:
    return await GeofenceService(session).create(payload)


@router.post(
    "/{geofence_id}/disable",
    response_model=GeofenceRead,
    summary="Disable a geofence",
    description="Disabled geofences stop generating enter/exit events.",
)
async def disable_geofence(
    _: AdminKey,
    session: DbSession,
    geofence_id: GeofenceId,
) -> GeofenceRead:
    return await GeofenceService(session).disable(geofence_id)
