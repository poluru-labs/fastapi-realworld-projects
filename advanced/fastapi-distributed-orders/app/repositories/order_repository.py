from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_with_items(self, order_id: int) -> Order | None:
        result = await self._session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Order]:
        result = await self._session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Order]:
        result = await self._session.execute(
            select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def add(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        await self._session.refresh(order, attribute_names=["items"])
        return order
