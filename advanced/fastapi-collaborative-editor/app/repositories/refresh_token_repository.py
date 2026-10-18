from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, jti: str) -> RefreshToken | None:
        return await self._session.get(RefreshToken, jti)

    async def save(self, *, jti: str, user_id: int, expires_at: datetime) -> None:
        self._session.add(RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at))

    async def revoke(self, jti: str) -> None:
        row = await self.get(jti)
        if row is not None:
            await self._session.delete(row)
