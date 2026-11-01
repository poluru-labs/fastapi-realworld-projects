from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import AuthorizationCode, OAuthClient, RefreshToken, User


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(select(User.id).where(User.email == email))
        return result.scalar_one_or_none() is not None

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def add_user(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_client_by_client_id(self, client_id: str) -> OAuthClient | None:
        result = await self._session.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def list_clients(self) -> list[OAuthClient]:
        result = await self._session.scalars(select(OAuthClient).order_by(OAuthClient.client_id))
        return list(result)

    async def add_client(self, client: OAuthClient) -> OAuthClient:
        self._session.add(client)
        await self._session.flush()
        return client

    async def get_auth_code_by_hash(self, code_hash: str) -> AuthorizationCode | None:
        result = await self._session.execute(
            select(AuthorizationCode).where(AuthorizationCode.code_hash == code_hash)
        )
        return result.scalar_one_or_none()

    async def add_auth_code(self, row: AuthorizationCode) -> AuthorizationCode:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def add_refresh_token(self, row: RefreshToken) -> RefreshToken:
        self._session.add(row)
        await self._session.flush()
        return row
