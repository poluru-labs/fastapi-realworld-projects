from fastapi import APIRouter

from app.api.deps import AdminKey, DbSession
from app.schemas.execution import PolicyRead, PolicyUpdate
from app.services.execution_service import ExecutionService

router = APIRouter()


@router.get(
    "",
    response_model=PolicyRead,
    summary="Read execution policy",
    description=(
        "Returns sandbox limits: max source bytes, wall-clock timeout, and allowed languages. "
        "Admin key required."
    ),
)
async def get_policy(_: AdminKey, session: DbSession) -> PolicyRead:
    return await ExecutionService(session).get_policy()


@router.patch(
    "",
    response_model=PolicyRead,
    summary="Update execution policy",
    description=(
        "Tune limits for educational runs. Production systems would use immutable policy "
        "versions and audit trails."
    ),
)
async def update_policy(
    _: AdminKey,
    session: DbSession,
    payload: PolicyUpdate,
) -> PolicyRead:
    return await ExecutionService(session).update_policy(payload)
