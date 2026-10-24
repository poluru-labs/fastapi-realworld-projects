from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.rate_limiting import RateLimitClient
from app.services.client_service import ClientService


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


async def require_client(
    session: DbSession,
    x_client_id: Annotated[str | None, Header(alias="X-Client-Id")] = None,
    x_client_key: Annotated[str | None, Header(alias="X-Client-Key")] = None,
) -> RateLimitClient:
    if not x_client_id or not x_client_id.strip():
        raise UnauthorizedError("Invalid or missing X-Client-Id")
    if not x_client_key or not x_client_key.strip():
        raise UnauthorizedError("Invalid or missing X-Client-Key")
    return await ClientService(session).verify_client_key(
        x_client_id.strip(),
        x_client_key.strip(),
    )


RateLimitClientDep = Annotated[RateLimitClient, Depends(require_client)]


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise ForbiddenError("Idempotency-Key header is required for quota consume")
    return idempotency_key.strip()[:128]


IdempotencyKey = Annotated[str, Depends(get_idempotency_key)]
