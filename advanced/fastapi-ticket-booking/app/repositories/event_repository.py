from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, TicketTier


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Event]:
        result = await self._session.execute(
            select(Event).options(selectinload(Event.tiers)).order_by(Event.starts_at)
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Event | None:
        result = await self._session.execute(
            select(Event).options(selectinload(Event.tiers)).where(Event.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, event_id: int) -> Event | None:
        result = await self._session.execute(
            select(Event).options(selectinload(Event.tiers)).where(Event.id == event_id)
        )
        return result.scalar_one_or_none()

    async def slug_taken(self, slug: str) -> bool:
        result = await self._session.execute(select(Event.id).where(Event.slug == slug))
        return result.scalar_one_or_none() is not None

    async def add(self, event: Event) -> Event:
        self._session.add(event)
        await self._session.flush()
        return event

    async def add_tier(self, tier: TicketTier) -> TicketTier:
        self._session.add(tier)
        await self._session.flush()
        return tier

    async def get_tier(self, tier_id: int) -> TicketTier | None:
        return await self._session.get(TicketTier, tier_id)
