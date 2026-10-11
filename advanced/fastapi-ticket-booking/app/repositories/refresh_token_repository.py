from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, *, jti: str, user_id: int, expires_at: datetime) -> None:
        self._session.add(RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at))
        await self._session.flush()

    async def get(self, jti: str) -> RefreshToken | None:
        return await self._session.get(RefreshToken, jti)

    async def revoke(self, jti: str) -> None:
        token = await self.get(jti)
        if token is not None:
            await self._session.delete(token)
