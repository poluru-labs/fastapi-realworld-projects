from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduler import ScheduledRun


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, run_id: int) -> ScheduledRun | None:
        return await self._session.get(ScheduledRun, run_id)

    async def list_for_owner(self, owner_id: int, *, limit: int, offset: int) -> list[ScheduledRun]:
        rows = await self._session.scalars(
            select(ScheduledRun)
            .where(ScheduledRun.owner_id == owner_id)
            .order_by(ScheduledRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows)

    async def find_claimable(
        self,
        *,
        task_types: list[str],
        now: datetime,
    ) -> ScheduledRun | None:
        stmt = (
            select(ScheduledRun)
            .where(
                ScheduledRun.status == "pending",
                ScheduledRun.task_type.in_(task_types),
                ScheduledRun.scheduled_for <= now,
                or_(
                    ScheduledRun.lease_expires_at.is_(None),
                    ScheduledRun.lease_expires_at < now,
                ),
            )
            .order_by(ScheduledRun.scheduled_for, ScheduledRun.id)
            .limit(1)
        )
        return await self._session.scalar(stmt)

    async def add(self, run: ScheduledRun) -> ScheduledRun:
        self._session.add(run)
        await self._session.flush()
        return run

    async def save(self) -> None:
        await self._session.flush()
