from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.rate_limiting import (
    KEY_PATTERN,
    ClientCreate,
    ClientProvisioned,
    ClientRead,
    SubjectUsageRow,
)
from app.services.client_service import ClientService

router = APIRouter()

ClientKey = Annotated[
    str,
    Path(pattern=KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[ClientRead],
    summary="List API clients",
    description="Admin key required. Secrets are never returned here.",
)
async def list_clients(_: AdminKey, session: DbSession) -> list[ClientRead]:
    return await ClientService(session).list_clients()


@router.post(
    "",
    response_model=ClientProvisioned,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a client",
    description="Returns a one-time **client_key** for the `X-Client-Key` header.",
)
async def provision_client(
    _: AdminKey,
    session: DbSession,
    payload: ClientCreate,
) -> ClientProvisioned:
    return await ClientService(session).provision(payload)


@router.get(
    "/{client_key}",
    response_model=ClientRead,
    summary="Get client metadata",
)
async def get_client(
    _: AdminKey,
    session: DbSession,
    client_key: ClientKey,
) -> ClientRead:
    return await ClientService(session).get_client(client_key)


@router.get(
    "/{client_key}/usage",
    response_model=list[SubjectUsageRow],
    summary="Current window usage by subject",
    description="Admin snapshot of counters in the active fixed window.",
)
async def client_usage(
    _: AdminKey,
    session: DbSession,
    client_key: ClientKey,
) -> list[SubjectUsageRow]:
    return await ClientService(session).usage_snapshot(client_key)
