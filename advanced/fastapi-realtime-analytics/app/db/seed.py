from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AlertRule, AnalyticsEvent, EventStream
from app.schemas.analytics import AlertStatus, StreamStatus


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(EventStream).where(EventStream.key == "web-traffic")
    )
    if existing is not None:
        return

    now = datetime.now(UTC)
    web = EventStream(
        key="web-traffic",
        name="Web traffic",
        description="Browser and API page views for the demo storefront.",
        status=StreamStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )
    checkout = EventStream(
        key="checkout",
        name="Checkout funnel",
        description="Paused stream used to show ingestion guards in /docs.",
        status=StreamStatus.PAUSED.value,
        created_at=now,
        updated_at=now,
    )
    session.add_all([web, checkout])
    await session.flush()

    events: list[AnalyticsEvent] = []
    for index in range(12):
        occurred = now - timedelta(minutes=index * 3)
        events.append(
            AnalyticsEvent(
                stream_id=web.id,
                event_name="page_view" if index % 2 == 0 else "button_click",
                occurred_at=occurred,
                properties={"path": "/home" if index % 3 else "/pricing"},
                dedupe_key=f"seed-{index}",
                ingested_at=occurred,
            )
        )
    session.add_all(events)

    session.add(
        AlertRule(
            stream_id=web.id,
            name="Traffic spike",
            window_minutes=15,
            threshold_count=20,
            status=AlertStatus.ENABLED.value,
            created_at=now,
        )
    )
    await session.commit()
