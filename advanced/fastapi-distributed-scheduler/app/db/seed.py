from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.scheduler import Schedule
from app.models.user import User
from app.schemas.scheduler import ScheduleKind, ScheduleStatus
from app.schemas.user import UserRole


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Scheduler Admin",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

    published = await session.scalar(
        select(Schedule).where(Schedule.slug == "nightly-report")
    )
    if published is None:
        now = datetime.now(UTC)
        session.add(
            Schedule(
                slug="nightly-report",
                name="Nightly report",
                description="Interval job for teaching worker claim and lease completion.",
                status=ScheduleStatus.PUBLISHED.value,
                schedule_kind=ScheduleKind.INTERVAL.value,
                interval_seconds=3600,
                cron_expression=None,
                timezone="UTC",
                task_type="report",
                default_payload={"format": "pdf"},
                max_attempts=3,
                retry_delay_seconds=30,
                owner_id=admin.id,
                published_at=now,
                created_at=now,
                updated_at=now,
            )
        )

    draft = await session.scalar(select(Schedule).where(Schedule.slug == "draft-cleanup"))
    if draft is None:
        session.add(
            Schedule(
                slug="draft-cleanup",
                name="Draft cleanup",
                description="Hidden until published.",
                status=ScheduleStatus.DRAFT.value,
                schedule_kind=ScheduleKind.CRON.value,
                cron_expression="0 3 * * *",
                interval_seconds=None,
                timezone="UTC",
                task_type="cleanup",
                default_payload={},
                max_attempts=2,
                retry_delay_seconds=60,
                owner_id=admin.id,
            )
        )

    await session.commit()
