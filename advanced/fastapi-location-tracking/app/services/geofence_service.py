from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.tracking import Geofence, GeofenceMonitor
from app.repositories.geofence_repository import GeofenceRepository
from app.repositories.tracker_repository import TrackerRepository
from app.schemas.tracking import (
    GeofenceCreate,
    GeofenceEventRead,
    GeofenceMonitorRead,
    GeofenceRead,
    GeofenceStatus,
)


class GeofenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._geofences = GeofenceRepository(session)
        self._trackers = TrackerRepository(session)

    async def list_geofences(self) -> list[GeofenceRead]:
        rows = await self._geofences.list_geofences()
        return [GeofenceRead.model_validate(row) for row in rows]

    async def create(self, payload: GeofenceCreate) -> GeofenceRead:
        if await self._geofences.get_geofence_by_name(payload.name) is not None:
            raise ConflictError("Geofence name already exists")
        now = datetime.now(UTC)
        row = Geofence(
            name=payload.name,
            center_latitude=payload.center_latitude,
            center_longitude=payload.center_longitude,
            radius_m=payload.radius_m,
            status=GeofenceStatus.ACTIVE.value,
            created_at=now,
        )
        await self._geofences.add_geofence(row)
        await self._session.commit()
        return GeofenceRead.model_validate(row)

    async def disable(self, geofence_id: int) -> GeofenceRead:
        row = await self._geofences.get_geofence(geofence_id)
        if row is None:
            raise NotFoundError("Geofence", str(geofence_id))
        if row.status == GeofenceStatus.DISABLED.value:
            raise ConflictError("Geofence is already disabled")
        row.status = GeofenceStatus.DISABLED.value
        await self._geofences.save()
        await self._session.commit()
        return GeofenceRead.model_validate(row)

    async def attach_monitor(self, tracker_key: str, geofence_id: int) -> GeofenceMonitorRead:
        tracker = await self._trackers.get_by_key(tracker_key)
        if tracker is None:
            raise NotFoundError("Tracker", tracker_key)
        geofence = await self._geofences.get_geofence(geofence_id)
        if geofence is None:
            raise NotFoundError("Geofence", str(geofence_id))
        monitors = await self._geofences.list_monitors_for_tracker(tracker.id)
        if any(m.geofence_id == geofence_id for m in monitors):
            raise ConflictError("Tracker is already monitored for this geofence")
        now = datetime.now(UTC)
        monitor = GeofenceMonitor(
            tracker_id=tracker.id,
            geofence_id=geofence_id,
            created_at=now,
        )
        await self._geofences.add_monitor(monitor)
        await self._session.commit()
        return GeofenceMonitorRead(
            tracker_id=tracker.id,
            tracker_key=tracker_key,
            geofence_id=geofence_id,
            geofence_name=geofence.name,
        )

    async def list_events(self, tracker_key: str, *, limit: int = 50) -> list[GeofenceEventRead]:
        tracker = await self._trackers.get_by_key(tracker_key)
        if tracker is None:
            raise NotFoundError("Tracker", tracker_key)
        rows = await self._geofences.list_events(tracker.id, limit=limit)
        return [GeofenceEventRead.model_validate(row) for row in rows]
