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


def get_experiment_token(
    x_experiment_token: Annotated[str | None, Header(alias="X-Experiment-Token")] = None,
) -> str:
    if not x_experiment_token or not x_experiment_token.strip():
        raise UnauthorizedError("Invalid or missing X-Experiment-Token")
    return x_experiment_token.strip()


ExperimentToken = Annotated[str, Depends(get_experiment_token)]


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise ForbiddenError("Idempotency-Key header is required for event ingest")
    return idempotency_key.strip()[:128]


IdempotencyKey = Annotated[str, Depends(get_idempotency_key)]
