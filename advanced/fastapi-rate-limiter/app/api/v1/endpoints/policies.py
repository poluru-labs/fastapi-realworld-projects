from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.rate_limiting import KEY_PATTERN, PolicyCreate, PolicyRead
from app.services.policy_service import PolicyService

router = APIRouter()

PolicyKey = Annotated[
    str,
    Path(pattern=KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[PolicyRead],
    summary="List rate limit policies",
    description="Admin key required.",
)
async def list_policies(_: AdminKey, session: DbSession) -> list[PolicyRead]:
    return await PolicyService(session).list_policies()


@router.post(
    "",
    response_model=PolicyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy",
    description="Fixed-window limit: `limit` requests per `window_seconds`.",
)
async def create_policy(
    _: AdminKey,
    session: DbSession,
    payload: PolicyCreate,
) -> PolicyRead:
    return await PolicyService(session).create_policy(payload)


@router.get(
    "/{policy_key}",
    response_model=PolicyRead,
    summary="Get a policy",
)
async def get_policy(
    _: AdminKey,
    session: DbSession,
    policy_key: PolicyKey,
) -> PolicyRead:
    return await PolicyService(session).get_policy(policy_key)


@router.post(
    "/{policy_key}/pause",
    response_model=PolicyRead,
    summary="Pause a policy",
    responses={409: {"description": "Already paused."}},
)
async def pause_policy(
    _: AdminKey,
    session: DbSession,
    policy_key: PolicyKey,
) -> PolicyRead:
    return await PolicyService(session).pause_policy(policy_key)


@router.post(
    "/{policy_key}/resume",
    response_model=PolicyRead,
    summary="Resume a policy",
    responses={409: {"description": "Already active."}},
)
async def resume_policy(
    _: AdminKey,
    session: DbSession,
    policy_key: PolicyKey,
) -> PolicyRead:
    return await PolicyService(session).resume_policy(policy_key)
