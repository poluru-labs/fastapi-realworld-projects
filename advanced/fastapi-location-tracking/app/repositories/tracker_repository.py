from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking import Tracker


class TrackerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Tracker]:
        result = await self._session.scalars(select(Tracker).order_by(Tracker.key))
        return list(result)

    async def get_by_key(self, key: str) -> Tracker | None:
        return await self._session.scalar(select(Tracker).where(Tracker.key == key))

    async def get_by_id(self, tracker_id: int) -> Tracker | None:
        return await self._session.get(Tracker, tracker_id)

    async def add(self, tracker: Tracker) -> Tracker:
        self._session.add(tracker)
        await self._session.flush()
        return tracker

    async def save(self) -> None:
        await self._session.flush()
