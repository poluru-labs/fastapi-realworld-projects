from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.models.membership import TenantRole
from app.repositories.membership_repository import MembershipRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessTokenResponse, RegisterRequest, RegisterResponse
from app.schemas.tenant import TenantRead
from app.schemas.user import UserRead


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._tenants = TenantRepository(session)
        self._memberships = MembershipRepository(session)

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
        token = create_access_token(settings=self._settings, user_id=user.id)
        await self._session.commit()
        return RegisterResponse(
            user=UserRead.model_validate(user),
            tenant=TenantRead.model_validate(tenant),
            tokens=AccessTokenResponse(access_token=token),
        )

    async def login(self, *, email: str, password: str) -> AccessTokenResponse:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        token = create_access_token(settings=self._settings, user_id=user.id)
        await self._session.commit()
        return AccessTokenResponse(access_token=token)
