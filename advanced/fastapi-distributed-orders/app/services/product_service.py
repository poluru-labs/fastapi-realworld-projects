from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductRead
from app.schemas.user import UserRead, UserRole


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._products = ProductRepository(session)

    async def list_products(self) -> list[ProductRead]:
        rows = await self._products.list_all()
        return [ProductRead.model_validate(row) for row in rows]

    async def create_product(self, actor: UserRead, payload: ProductCreate) -> ProductRead:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only admins can add catalog items")
        if await self._products.get_by_sku(payload.sku) is not None:
            raise ConflictError("SKU already exists")
        product = await self._products.create(
            sku=payload.sku,
            name=payload.name,
            price_cents=payload.price_cents,
            stock_quantity=payload.stock_quantity,
        )
        await self._session.commit()
        return ProductRead.model_validate(product)
