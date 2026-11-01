from fastapi import APIRouter, status

from app.api.deps import AdminKey, AppSettings, DbSession
from app.schemas.identity import ClientCreate, ClientCreated, ClientRead
from app.services.identity_service import IdentityService

router = APIRouter()


@router.get(
    "",
    response_model=list[ClientRead],
    summary="List OAuth clients",
    description="Admin-only. Secrets are never returned from list endpoints.",
)
async def list_clients(_: AdminKey, session: DbSession, settings: AppSettings) -> list[ClientRead]:
    return await IdentityService(session, settings).list_clients()


@router.post(
    "",
    response_model=ClientCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Register an OAuth client",
    description=(
        "Returns `client_secret` once. Store hashes only — mirror production identity providers."
    ),
)
async def create_client(
    _: AdminKey,
    session: DbSession,
    settings: AppSettings,
    payload: ClientCreate,
) -> ClientCreated:
    return await IdentityService(session, settings).create_client(payload)
