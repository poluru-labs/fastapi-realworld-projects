from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking import Geofence, GeofenceEvent, GeofenceMonitor, GeofenceState


class GeofenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_geofences(self) -> list[Geofence]:
        result = await self._session.scalars(select(Geofence).order_by(Geofence.name))
        return list(result)

    async def get_geofence(self, geofence_id: int) -> Geofence | None:
        return await self._session.get(Geofence, geofence_id)

    async def get_geofence_by_name(self, name: str) -> Geofence | None:
        return await self._session.scalar(select(Geofence).where(Geofence.name == name))

    async def add_geofence(self, geofence: Geofence) -> Geofence:
        self._session.add(geofence)
        await self._session.flush()
        return geofence

    async def save(self) -> None:
        await self._session.flush()

    async def list_monitors_for_tracker(self, tracker_id: int) -> list[GeofenceMonitor]:
        result = await self._session.scalars(
            select(GeofenceMonitor).where(GeofenceMonitor.tracker_id == tracker_id)
        )
        return list(result)

    async def monitor_count(self, tracker_id: int) -> int:
        result = await self._session.scalars(
            select(GeofenceMonitor).where(GeofenceMonitor.tracker_id == tracker_id)
        )
        return len(list(result))

    async def add_monitor(self, monitor: GeofenceMonitor) -> GeofenceMonitor:
        self._session.add(monitor)
        await self._session.flush()
        return monitor

    async def get_state(self, tracker_id: int, geofence_id: int) -> GeofenceState | None:
        return await self._session.scalar(
            select(GeofenceState).where(
                GeofenceState.tracker_id == tracker_id,
                GeofenceState.geofence_id == geofence_id,
            )
        )

    async def upsert_state(self, state: GeofenceState) -> GeofenceState:
        existing = await self.get_state(state.tracker_id, state.geofence_id)
        if existing is None:
            self._session.add(state)
            await self._session.flush()
            return state
        existing.inside = state.inside
        existing.updated_at = state.updated_at
        await self._session.flush()
        return existing

    async def add_event(self, event: GeofenceEvent) -> GeofenceEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_events(
        self,
        tracker_id: int,
        *,
        limit: int,
    ) -> list[GeofenceEvent]:
        result = await self._session.scalars(
            select(GeofenceEvent)
            .where(GeofenceEvent.tracker_id == tracker_id)
            .order_by(GeofenceEvent.occurred_at.desc(), GeofenceEvent.id.desc())
            .limit(limit)
        )
        return list(result)
