from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.device_tokens import hash_device_token
from app.models.telemetry import Device, TelemetryAlertRule, TelemetryReading
from app.schemas.telemetry import AlertStatus, Comparator, DeviceStatus

SEED_DEVICE_TOKEN = "seed-token-warehouse-temp-01"


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(Device).where(Device.key == "warehouse-temp-01")
    )
    if existing is not None:
        return

    now = datetime.now(UTC)
    device = Device(
        key="warehouse-temp-01",
        name="Warehouse temperature",
        site="Building A",
        status=DeviceStatus.ACTIVE.value,
        ingest_token_hash=hash_device_token(SEED_DEVICE_TOKEN),
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    suspended = Device(
        key="legacy-pump-02",
        name="Legacy pump controller",
        site="Building B",
        status=DeviceStatus.SUSPENDED.value,
        ingest_token_hash=hash_device_token("seed-token-legacy-pump"),
        last_seen_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add_all([device, suspended])
    await session.flush()

    readings: list[TelemetryReading] = []
    for index in range(10):
        recorded = now - timedelta(minutes=index * 6)
        readings.append(
            TelemetryReading(
                device_id=device.id,
                recorded_at=recorded,
                metrics={"temp_c": 20.0 + index * 0.5, "humidity_pct": 40 + index},
                dedupe_key=f"seed-{index}",
                ingested_at=recorded,
            )
        )
    session.add_all(readings)

    session.add(
        TelemetryAlertRule(
            device_id=device.id,
            name="High temperature",
            metric_key="temp_c",
            window_minutes=60,
            threshold=28.0,
            comparator=Comparator.GTE.value,
            status=AlertStatus.ENABLED.value,
            created_at=now,
        )
    )
    await session.commit()
