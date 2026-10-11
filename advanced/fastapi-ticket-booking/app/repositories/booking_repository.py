from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_with_items(self, booking_id: int) -> Booking | None:
        result = await self._session.execute(
            select(Booking).options(selectinload(Booking.items)).where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Booking]:
        result = await self._session.execute(
            select(Booking)
            .options(selectinload(Booking.items))
            .where(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Booking]:
        result = await self._session.execute(
            select(Booking).options(selectinload(Booking.items)).order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def add(self, booking: Booking) -> Booking:
        self._session.add(booking)
        await self._session.flush()
        return booking
