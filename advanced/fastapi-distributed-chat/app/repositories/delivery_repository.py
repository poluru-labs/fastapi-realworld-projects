from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRoom, DeliveryOutbox


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, delivery_id: int) -> DeliveryOutbox | None:
        return await self._session.get(DeliveryOutbox, delivery_id)

    async def find_claimable(
        self,
        *,
        room_slugs: list[str],
        now: datetime,
    ) -> DeliveryOutbox | None:
        stmt = (
            select(DeliveryOutbox)
            .join(ChatRoom, ChatRoom.id == DeliveryOutbox.room_id)
            .where(
                DeliveryOutbox.status == "pending",
                or_(
                    DeliveryOutbox.lease_expires_at.is_(None),
                    DeliveryOutbox.lease_expires_at < now,
                ),
            )
            .order_by(DeliveryOutbox.created_at, DeliveryOutbox.id)
            .limit(1)
        )
        if room_slugs:
            stmt = stmt.where(ChatRoom.slug.in_(room_slugs))
        return await self._session.scalar(stmt)

    async def save(self) -> None:
        await self._session.flush()
