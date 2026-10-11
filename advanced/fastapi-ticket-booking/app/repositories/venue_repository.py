from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue import Venue


class VenueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Venue]:
        result = await self._session.execute(select(Venue).order_by(Venue.name))
        return list(result.scalars().all())

    async def get(self, venue_id: int) -> Venue | None:
        return await self._session.get(Venue, venue_id)

    async def create(self, *, name: str, city: str) -> Venue:
        venue = Venue(name=name, city=city)
        self._session.add(venue)
        await self._session.flush()
        return venue
