from typing import Annotated

from fastapi import APIRouter, Body

from app.api.deps import CurrentUser, SyncServiceDep
from app.schemas.editor import (
    ClaimSyncRequest,
    CompleteSyncRequest,
    SyncHeartbeat,
    SyncRead,
    SyncRegister,
)

router = APIRouter(prefix="/sync", tags=["sync"])

_REGISTER_EXAMPLES = {
    "edge": {
        "summary": "Node scoped to one document",
        "value": {"node_id": "edge-us-west", "document_slugs": ["team-playbook"]},
    }
}


@router.post("/register", summary="Register a sync node")
async def register_sync_node(
    payload: Annotated[SyncRegister, Body(openapi_examples=_REGISTER_EXAMPLES)],
    service: SyncServiceDep,
    user: CurrentUser,
) -> dict[str, str]:
    return await service.register_node(user, payload)


@router.post("/heartbeat", summary="Refresh sync node liveness")
async def sync_heartbeat(
    payload: SyncHeartbeat,
    service: SyncServiceDep,
    user: CurrentUser,
) -> dict[str, str]:
    return await service.heartbeat(user, payload)


@router.post(
    "/claim",
    response_model=SyncRead,
    summary="Claim the next pending sync job",
)
async def claim_sync(
    payload: ClaimSyncRequest,
    service: SyncServiceDep,
    user: CurrentUser,
) -> SyncRead:
    return await service.claim(user, payload)


@router.post(
    "/jobs/{sync_id}/complete",
    response_model=SyncRead,
    summary="Mark a leased sync job complete",
)
async def complete_sync(
    sync_id: int,
    payload: CompleteSyncRequest,
    service: SyncServiceDep,
    user: CurrentUser,
) -> SyncRead:
    return await service.complete(user, sync_id, payload)
