from fastapi import APIRouter, status

from app.api.deps import AdminKey, AppSettings, CurrentUser, DbSession
from app.schemas.policy import (
    EvaluateRequest,
    EvaluateResponse,
    PolicyRuleCreate,
    PolicyRuleRead,
    RoleAssignment,
    RoleRead,
    UserRead,
)
from app.services.policy_service import PolicyService

router = APIRouter()


@router.get(
    "/roles",
    response_model=list[RoleRead],
    summary="List roles",
    description="Admin-only reference for role slugs used in policy rules.",
)
async def list_roles(_: AdminKey, session: DbSession, settings: AppSettings) -> list[RoleRead]:
    return await PolicyService(session, settings).list_roles()


@router.post(
    "/role-assignments",
    response_model=UserRead,
    summary="Assign a role to a user",
)
async def assign_role(
    _: AdminKey,
    session: DbSession,
    settings: AppSettings,
    payload: RoleAssignment,
) -> UserRead:
    return await PolicyService(session, settings).assign_role(payload)


@router.get(
    "/rules",
    response_model=list[PolicyRuleRead],
    summary="List policy rules",
)
async def list_rules(
    _: AdminKey,
    session: DbSession,
    settings: AppSettings,
) -> list[PolicyRuleRead]:
    return await PolicyService(session, settings).list_policies()


@router.post(
    "/rules",
    response_model=PolicyRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy rule",
    description=(
        "Rules match `action` (supports `documents:*` wildcards), `resource` patterns "
        "(`document/*`), optional role requirements, and optional clearance ABAC."
    ),
)
async def create_rule(
    _: AdminKey,
    session: DbSession,
    settings: AppSettings,
    payload: PolicyRuleCreate,
) -> PolicyRuleRead:
    return await PolicyService(session, settings).create_policy(payload)


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate authorization",
    description=(
        "Central policy decision point. Pass `resource_attributes` such as "
        "`{\"classification\": \"secret\"}` to exercise ABAC clearance checks."
    ),
)
async def evaluate(
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    payload: EvaluateRequest,
) -> EvaluateResponse:
    return await PolicyService(session, settings).evaluate(user.id, payload)
