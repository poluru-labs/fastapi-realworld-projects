from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserRole


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        session.add(
            User(
                email="admin@example.com",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Webhook Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
        )
    await session.commit()
