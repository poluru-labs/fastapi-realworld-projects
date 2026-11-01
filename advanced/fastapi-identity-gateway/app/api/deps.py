from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.repositories.identity_repository import IdentityRepository
from app.schemas.identity import UserRead

_bearer = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def require_admin_key(
    settings: AppSettings,
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if x_admin_key is None or x_admin_key != settings.admin_api_key:
        raise UnauthorizedError("Invalid or missing X-Admin-Key")


AdminKey = Annotated[None, Depends(require_admin_key)]


async def get_current_user(
    session: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserRead:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    payload = decode_access_token(settings=settings, token=credentials.credentials)
    sub = payload.get("sub")
    if sub is None or not str(sub).isdigit():
        raise UnauthorizedError("User session required")
    user = await IdentityRepository(session).get_user_by_id(int(sub))
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return UserRead.model_validate(user)


CurrentUser = Annotated[UserRead, Depends(get_current_user)]
