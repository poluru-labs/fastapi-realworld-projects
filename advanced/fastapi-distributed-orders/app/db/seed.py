from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.product import Product
from app.models.user import User, UserRole


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        session.add(
            User(
                email="admin@example.com",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Ops Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
        )

    for sku, name, price, stock in (
        ("WIDGET-1", "Widget One", 999, 100),
        ("GADGET-2", "Gadget Two", 2499, 50),
    ):
        exists = await session.scalar(select(Product).where(Product.sku == sku))
        if exists is None:
            session.add(
                Product(sku=sku, name=name, price_cents=price, stock_quantity=stock),
            )

    await session.commit()
