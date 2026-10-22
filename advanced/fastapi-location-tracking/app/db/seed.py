from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.geo import inside_geofence
from app.core.tracker_tokens import hash_tracker_token
from app.models.tracking import (
    Geofence,
    GeofenceMonitor,
    GeofenceState,
    LocationPing,
    Tracker,
)
from app.schemas.tracking import GeofenceStatus, TrackerStatus

SEED_TRACKER_TOKEN = "seed-token-delivery-van-01"


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(select(Tracker).where(Tracker.key == "delivery-van-01"))
    if existing is not None:
        return

    now = datetime.now(UTC)
    tracker = Tracker(
        key="delivery-van-01",
        name="Delivery van 01",
        status=TrackerStatus.ACTIVE.value,
        ingest_token_hash=hash_tracker_token(SEED_TRACKER_TOKEN),
        last_latitude=37.7749,
        last_longitude=-122.4194,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(tracker)
    await session.flush()

    geofence = Geofence(
        name="SF depot",
        center_latitude=37.7749,
        center_longitude=-122.4194,
        radius_m=500.0,
        status=GeofenceStatus.ACTIVE.value,
        created_at=now,
    )
    session.add(geofence)
    await session.flush()

    session.add(
        GeofenceMonitor(
            tracker_id=tracker.id,
            geofence_id=geofence.id,
            created_at=now,
        )
    )
    inside = inside_geofence(
        lat=tracker.last_latitude,
        lon=tracker.last_longitude,
        center_lat=geofence.center_latitude,
        center_lon=geofence.center_longitude,
        radius_m=geofence.radius_m,
    )
    session.add(
        GeofenceState(
            tracker_id=tracker.id,
            geofence_id=geofence.id,
            inside=inside,
            updated_at=now,
        )
    )

    pings: list[LocationPing] = []
    for index in range(5):
        recorded = now - timedelta(minutes=index * 10)
        pings.append(
            LocationPing(
                tracker_id=tracker.id,
                latitude=37.7749 + index * 0.0001,
                longitude=-122.4194,
                accuracy_m=12.0,
                recorded_at=recorded,
                dedupe_key=f"seed-{index}",
                ingested_at=recorded,
            )
        )
    session.add_all(pings)
    await session.commit()
