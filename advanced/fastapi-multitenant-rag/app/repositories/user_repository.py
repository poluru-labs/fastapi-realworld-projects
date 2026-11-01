from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(select(User.id).where(User.email == email))
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, password: str, full_name: str) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user
