from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserRole
from app.services.http_client import default_webhook_client

_bearer = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_webhook_http_client(request: Request) -> AsyncIterator[httpx.AsyncClient]:
    client = getattr(request.app.state, "webhook_http_client", None)
    if client is not None:
        yield client
        return
    async with default_webhook_client() as owned:
        yield owned


WebhookHttpClient = Annotated[httpx.AsyncClient, Depends(get_webhook_http_client)]


async def _user_from_token(
    session: AsyncSession,
    settings: Settings,
    token: str,
) -> UserRead:
    payload = decode_token(settings=settings, token=token, expected_type="access")
    user_id = int(payload["sub"])
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return UserRead.model_validate(user)


async def get_current_user(
    session: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserRead:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    return await _user_from_token(session, settings, credentials.credentials)


CurrentUser = Annotated[UserRead, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> UserRead:
    if user.role is not UserRole.ADMIN:
        raise ForbiddenError("Admin role required")
    return user


AdminUser = Annotated[UserRead, Depends(require_admin)]


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise ForbiddenError("Idempotency-Key header is required for this operation")
    return idempotency_key.strip()[:128]


IdempotencyKey = Annotated[str, Depends(get_idempotency_key)]
