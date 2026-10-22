from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.tracker_tokens import generate_tracker_token, hash_tracker_token, verify_tracker_token
from app.models.tracking import Tracker
from app.repositories.geofence_repository import GeofenceRepository
from app.repositories.location_repository import LocationRepository
from app.repositories.tracker_repository import TrackerRepository
from app.schemas.tracking import (
    TrackerCreate,
    TrackerOverview,
    TrackerProvisioned,
    TrackerRead,
    TrackerStatus,
)


class TrackerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trackers = TrackerRepository(session)
        self._locations = LocationRepository(session)
        self._geofences = GeofenceRepository(session)

    async def list_trackers(self) -> list[TrackerRead]:
        rows = await self._trackers.list_all()
        return [TrackerRead.model_validate(row) for row in rows]

    async def get_tracker(self, key: str) -> TrackerRead:
        return TrackerRead.model_validate(await self._require_tracker(key))

    async def provision(self, payload: TrackerCreate) -> TrackerProvisioned:
        if await self._trackers.get_by_key(payload.key) is not None:
            raise ConflictError("Another tracker already uses this key")
        token = generate_tracker_token()
        now = datetime.now(UTC)
        tracker = Tracker(
            key=payload.key,
            name=payload.name,
            status=TrackerStatus.ACTIVE.value,
            ingest_token_hash=hash_tracker_token(token),
            last_latitude=None,
            last_longitude=None,
            last_seen_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._trackers.add(tracker)
        await self._session.commit()
        body = TrackerRead.model_validate(tracker)
        return TrackerProvisioned(**body.model_dump(), ingest_token=token)

    async def suspend(self, key: str) -> TrackerRead:
        tracker = await self._require_tracker(key)
        if tracker.status == TrackerStatus.SUSPENDED.value:
            raise ConflictError("Tracker is already suspended")
        tracker.status = TrackerStatus.SUSPENDED.value
        tracker.updated_at = datetime.now(UTC)
        await self._trackers.save()
        await self._session.commit()
        return TrackerRead.model_validate(tracker)

    async def resume(self, key: str) -> TrackerRead:
        tracker = await self._require_tracker(key)
        if tracker.status == TrackerStatus.DECOMMISSIONED.value:
            raise ConflictError("Decommissioned trackers cannot resume")
        if tracker.status == TrackerStatus.ACTIVE.value:
            raise ConflictError("Tracker is already active")
        tracker.status = TrackerStatus.ACTIVE.value
        tracker.updated_at = datetime.now(UTC)
        await self._trackers.save()
        await self._session.commit()
        return TrackerRead.model_validate(tracker)

    async def overview(self, key: str) -> TrackerOverview:
        tracker = await self._require_tracker(key)
        now = datetime.now(UTC)
        since = now - timedelta(hours=1)
        return TrackerOverview(
            tracker_key=tracker.key,
            status=TrackerStatus(tracker.status),
            total_pings=await self._locations.count_for_tracker(tracker.id),
            pings_last_hour=await self._locations.count_since(tracker.id, since),
            last_seen_at=tracker.last_seen_at,
            last_latitude=tracker.last_latitude,
            last_longitude=tracker.last_longitude,
            monitored_geofences=await self._geofences.monitor_count(tracker.id),
        )

    async def verify_ingest_token(self, key: str, token: str) -> Tracker:
        tracker = await self._require_tracker(key)
        if tracker.status != TrackerStatus.ACTIVE.value:
            raise ConflictError("Tracker is not accepting location pings")
        if not verify_tracker_token(token, tracker.ingest_token_hash):
            raise UnauthorizedError("Invalid tracker ingest token")
        return tracker

    async def touch_location(
        self,
        tracker: Tracker,
        *,
        latitude: float,
        longitude: float,
        when: datetime,
    ) -> None:
        tracker.last_latitude = latitude
        tracker.last_longitude = longitude
        tracker.last_seen_at = when
        tracker.updated_at = datetime.now(UTC)
        await self._trackers.save()

    async def _require_tracker(self, key: str) -> Tracker:
        tracker = await self._trackers.get_by_key(key)
        if tracker is None:
            raise NotFoundError("Tracker", key)
        return tracker
