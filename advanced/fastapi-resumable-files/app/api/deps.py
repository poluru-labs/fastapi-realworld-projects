from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError


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


def get_upload_token(
    x_upload_token: Annotated[str | None, Header(alias="X-Upload-Token")] = None,
) -> str:
    if not x_upload_token or not x_upload_token.strip():
        raise UnauthorizedError("Invalid or missing X-Upload-Token")
    return x_upload_token.strip()


UploadToken = Annotated[str, Depends(get_upload_token)]


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise ForbiddenError("Idempotency-Key header is required for part uploads")
    return idempotency_key.strip()[:128]


IdempotencyKey = Annotated[str, Depends(get_idempotency_key)]


def get_part_index(
    x_part_index: Annotated[int | None, Header(alias="X-Part-Index")] = None,
) -> int:
    if x_part_index is None or x_part_index < 0:
        raise ForbiddenError("X-Part-Index header is required and must be >= 0")
    return x_part_index


PartIndex = Annotated[int, Depends(get_part_index)]
