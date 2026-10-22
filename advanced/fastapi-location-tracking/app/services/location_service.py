import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.geo import inside_geofence
from app.models.tracking import (
    GeofenceEvent,
    GeofenceState,
    LocationIdempotencyRecord,
    LocationPing,
)
from app.repositories.geofence_repository import GeofenceRepository
from app.repositories.location_repository import LocationRepository
from app.repositories.tracker_repository import TrackerRepository
from app.schemas.tracking import (
    GeofenceEventRead,
    GeofenceEventType,
    GeofenceStatus,
    LocationIngest,
    LocationIngestResult,
    LocationRead,
    LocationTrail,
)
from app.services.tracker_service import TrackerService


class LocationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trackers = TrackerRepository(session)
        self._locations = LocationRepository(session)
        self._geofences = GeofenceRepository(session)
        self._tracker_svc = TrackerService(session)

    async def ingest(
        self,
        tracker_key: str,
        token: str,
        idempotency_key: str,
        payload: LocationIngest,
    ) -> LocationIngestResult:
        tracker = await self._tracker_svc.verify_ingest_token(tracker_key, token)
        existing = await self._locations.get_idempotency(tracker.id, idempotency_key)
        if existing is not None:
            return LocationIngestResult.model_validate(json.loads(existing.response_json))

        dedupe = payload.dedupe_key or idempotency_key
        if await self._locations.dedupe_exists(tracker.id, dedupe):
            raise ConflictError("Duplicate location ping (dedupe_key)")

        now = datetime.now(UTC)
        recorded_at = payload.recorded_at if payload.recorded_at is not None else now
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)

        ping = LocationPing(
            tracker_id=tracker.id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            recorded_at=recorded_at,
            dedupe_key=dedupe,
            ingested_at=now,
        )
        await self._locations.add_ping(ping)
        await self._tracker_svc.touch_location(
            tracker,
            latitude=payload.latitude,
            longitude=payload.longitude,
            when=recorded_at,
        )

        events: list[GeofenceEventRead] = []
        monitors = await self._geofences.list_monitors_for_tracker(tracker.id)
        for monitor in monitors:
            geofence = await self._geofences.get_geofence(monitor.geofence_id)
            if geofence is None or geofence.status != GeofenceStatus.ACTIVE.value:
                continue
            now_inside = inside_geofence(
                lat=payload.latitude,
                lon=payload.longitude,
                center_lat=geofence.center_latitude,
                center_lon=geofence.center_longitude,
                radius_m=geofence.radius_m,
            )
            state = await self._geofences.get_state(tracker.id, geofence.id)
            was_inside = state.inside if state is not None else False

            if now_inside and not was_inside:
                ev = GeofenceEvent(
                    tracker_id=tracker.id,
                    geofence_id=geofence.id,
                    event_type=GeofenceEventType.ENTER.value,
                    latitude=payload.latitude,
                    longitude=payload.longitude,
                    occurred_at=recorded_at,
                )
                saved = await self._geofences.add_event(ev)
                events.append(GeofenceEventRead.model_validate(saved))
            elif not now_inside and was_inside:
                ev = GeofenceEvent(
                    tracker_id=tracker.id,
                    geofence_id=geofence.id,
                    event_type=GeofenceEventType.EXIT.value,
                    latitude=payload.latitude,
                    longitude=payload.longitude,
                    occurred_at=recorded_at,
                )
                saved = await self._geofences.add_event(ev)
                events.append(GeofenceEventRead.model_validate(saved))

            await self._geofences.upsert_state(
                GeofenceState(
                    tracker_id=tracker.id,
                    geofence_id=geofence.id,
                    inside=now_inside,
                    updated_at=now,
                )
            )

        result = LocationIngestResult(
            ping=LocationRead.model_validate(ping),
            geofence_events=events,
        )
        await self._locations.add_idempotency(
            LocationIdempotencyRecord(
                tracker_id=tracker.id,
                idempotency_key=idempotency_key,
                response_json=result.model_dump_json(),
                status_code=201,
            )
        )
        await self._session.commit()
        return result

    async def trail(self, tracker_key: str, *, window_minutes: int) -> LocationTrail:
        tracker = await self._trackers.get_by_key(tracker_key)
        if tracker is None:
            raise NotFoundError("Tracker", tracker_key)
        since = datetime.now(UTC) - timedelta(minutes=window_minutes)
        pings = await self._locations.list_since(tracker.id, since)
        return LocationTrail(
            tracker_key=tracker_key,
            window_minutes=window_minutes,
            points=[LocationRead.model_validate(p) for p in pings],
        )
