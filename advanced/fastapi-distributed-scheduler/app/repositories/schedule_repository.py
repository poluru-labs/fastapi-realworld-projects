from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduler import Schedule


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Schedule | None:
        return await self._session.scalar(select(Schedule).where(Schedule.slug == slug))

    async def list_published(self) -> list[Schedule]:
        rows = await self._session.scalars(
            select(Schedule)
            .where(Schedule.status == "published")
            .order_by(Schedule.published_at.desc(), Schedule.id.desc())
        )
        return list(rows)

    async def list_for_owner(self, owner_id: int) -> list[Schedule]:
        rows = await self._session.scalars(
            select(Schedule)
            .where(Schedule.owner_id == owner_id)
            .order_by(Schedule.updated_at.desc())
        )
        return list(rows)

    async def add(self, schedule: Schedule) -> Schedule:
        self._session.add(schedule)
        await self._session.flush()
        return schedule

    async def save(self) -> None:
        await self._session.flush()
