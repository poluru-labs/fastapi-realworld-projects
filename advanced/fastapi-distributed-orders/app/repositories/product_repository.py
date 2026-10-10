from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Product]:
        result = await self._session.execute(select(Product).order_by(Product.sku))
        return list(result.scalars().all())

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self._session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        sku: str,
        name: str,
        price_cents: int,
        stock_quantity: int,
    ) -> Product:
        product = Product(
            sku=sku,
            name=name,
            price_cents=price_cents,
            stock_quantity=stock_quantity,
        )
        self._session.add(product)
        await self._session.flush()
        return product

    async def reserve(self, *, sku: str, quantity: int) -> bool:
        result = await self._session.execute(
            update(Product)
            .where(Product.sku == sku, Product.stock_quantity >= quantity)
            .values(stock_quantity=Product.stock_quantity - quantity)
        )
        return result.rowcount == 1

    async def release(self, *, sku: str, quantity: int) -> None:
        await self._session.execute(
            update(Product)
            .where(Product.sku == sku)
            .values(stock_quantity=Product.stock_quantity + quantity)
        )
