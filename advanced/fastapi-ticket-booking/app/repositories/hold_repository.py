from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hold import HoldStatus, TicketHold


class HoldRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def expire_stale(self) -> int:
        now = datetime.now(UTC)
        result = await self._session.execute(
            update(TicketHold)
            .where(
                TicketHold.status == HoldStatus.ACTIVE.value,
                TicketHold.expires_at < now,
            )
            .values(status=HoldStatus.EXPIRED.value)
        )
        return result.rowcount or 0

    async def active_quantity_for_tier(self, tier_id: int) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(TicketHold.quantity), 0)).where(
                TicketHold.tier_id == tier_id,
                TicketHold.status == HoldStatus.ACTIVE.value,
            )
        )
        return int(result.scalar_one())

    async def get(self, hold_id: int) -> TicketHold | None:
        return await self._session.get(TicketHold, hold_id)

    async def list_active_for_user(self, user_id: int) -> list[TicketHold]:
        result = await self._session.execute(
            select(TicketHold)
            .where(
                TicketHold.user_id == user_id,
                TicketHold.status == HoldStatus.ACTIVE.value,
            )
            .order_by(TicketHold.expires_at)
        )
        return list(result.scalars().all())

    async def add(self, hold: TicketHold) -> TicketHold:
        self._session.add(hold)
        await self._session.flush()
        return hold

    async def save(self, hold: TicketHold) -> None:
        await self._session.flush()
