from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_token
from app.models.membership import TenantRole
from app.repositories.membership_repository import MembershipRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.tenant import TenantRead
from app.schemas.user import UserRead

_bearer = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    session: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserRead:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    payload = decode_token(
        settings=settings,
        token=credentials.credentials,
        expected_type="access",
    )
    user_id = int(payload["sub"])
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return UserRead.model_validate(user)


CurrentUser = Annotated[UserRead, Depends(get_current_user)]


@dataclass(frozen=True)
class TenantContext:
    tenant: TenantRead
    role: TenantRole


async def get_tenant_context(
    session: DbSession,
    user: CurrentUser,
    x_tenant_slug: Annotated[str | None, Header(alias="X-Tenant-Slug")] = None,
) -> TenantContext:
    if not x_tenant_slug:
        raise ForbiddenError("Missing X-Tenant-Slug header for tenant-scoped routes")

    tenant = await TenantRepository(session).get_by_slug(x_tenant_slug.strip().lower())
    if tenant is None or not tenant.is_active:
        raise NotFoundError("Tenant", x_tenant_slug)

    membership = await MembershipRepository(session).get(tenant_id=tenant.id, user_id=user.id)
    if membership is None:
        raise ForbiddenError("You are not a member of this tenant")

    return TenantContext(
        tenant=TenantRead.model_validate(tenant),
        role=TenantRole(membership.role),
    )


ActiveTenant = Annotated[TenantContext, Depends(get_tenant_context)]
