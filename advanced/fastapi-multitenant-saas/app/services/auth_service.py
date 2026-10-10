from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.membership import TenantRole
from app.repositories.membership_repository import MembershipRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, RegisterResponse, TokenPair
from app.schemas.tenant import TenantRead
from app.schemas.user import UserRead


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._tenants = TenantRepository(session)
        self._memberships = MembershipRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

    async def register(self, payload: RegisterRequest) -> RegisterResponse:
        if await self._users.email_exists(payload.email):
            raise ConflictError("Email already registered")
        if await self._tenants.slug_exists(payload.tenant_slug):
            raise ConflictError("Tenant slug already taken")

        user = await self._users.create(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
        tenant = await self._tenants.create(name=payload.tenant_name, slug=payload.tenant_slug)
        await self._memberships.create(
            tenant_id=tenant.id,
            user_id=user.id,
            role=TenantRole.OWNER,
        )
        tokens = await self._issue_token_pair(user_id=user.id)
        await self._session.commit()
        return RegisterResponse(
            user=UserRead.model_validate(user),
            tenant=TenantRead.model_validate(tenant),
            tokens=tokens,
        )

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        tokens = await self._issue_token_pair(user_id=user.id)
        await self._session.commit()
        return tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(
            settings=self._settings,
            token=refresh_token,
            expected_type="refresh",
        )
        jti = str(payload["jti"])
        stored = await self._refresh_tokens.get(jti)
        if stored is None:
            raise UnauthorizedError("Refresh token revoked or unknown")

        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            await self._refresh_tokens.revoke(jti)
            await self._session.commit()
            raise UnauthorizedError("Refresh token expired")

        user_id = int(payload["sub"])
        if stored.user_id != user_id:
            raise UnauthorizedError()

        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError()

        await self._refresh_tokens.revoke(jti)
        tokens = await self._issue_token_pair(user_id=user.id)
        await self._session.commit()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        payload = decode_token(
            settings=self._settings,
            token=refresh_token,
            expected_type="refresh",
        )
        await self._refresh_tokens.revoke(str(payload["jti"]))
        await self._session.commit()

    async def _issue_token_pair(self, *, user_id: int) -> TokenPair:
        access = create_access_token(settings=self._settings, user_id=user_id)
        refresh, jti, expires_at = create_refresh_token(settings=self._settings, user_id=user_id)
        await self._refresh_tokens.save(jti=jti, user_id=user_id, expires_at=expires_at)
        return TokenPair(access_token=access, refresh_token=refresh)
