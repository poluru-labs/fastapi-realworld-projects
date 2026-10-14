from typing import Annotated

from fastapi import APIRouter, Body, status

from app.api.deps import CurrentUser, DbSession, IdempotencyKey
from app.schemas.workflow import (
    InstanceStart,
    TransitionCommand,
    WorkflowEventRead,
    WorkflowInstanceRead,
)
from app.services.instance_service import InstanceService

router = APIRouter(prefix="/workflow-instances", tags=["workflow-instances"])

_START_EXAMPLES = {
    "onboarding": {
        "summary": "Start employee onboarding",
        "description": (
            "Requires a **published** definition slug. "
            "Send a unique **Idempotency-Key** header so retries are safe."
        ),
        "value": {
            "definition_slug": "employee-onboarding",
            "context": {"employee_email": "new.hire@example.com"},
        },
    }
}

_TRANSITION_EXAMPLES = {
    "profile": {
        "summary": "Advance with optimistic version",
        "description": (
            "Use `expected_version` from your last GET. "
            "Admin-only actions include `approve` and `activate` on the seed workflow."
        ),
        "value": {
            "action": "complete_profile",
            "expected_version": 1,
            "context_patch": {"profile_completed": True},
            "note": "Submitted HR form",
        },
    }
}


@router.get(
    "",
    response_model=list[WorkflowInstanceRead],
    summary="List workflow instances",
    description="Customers see their instances. Platform admins see every instance.",
)
async def list_instances(user: CurrentUser, session: DbSession) -> list[WorkflowInstanceRead]:
    return await InstanceService(session).list_instances(user)


@router.get(
    "/{instance_id}",
    response_model=WorkflowInstanceRead,
    summary="Get one workflow instance",
    description="Another user's instance id returns **404**, not **403**.",
)
async def get_instance(
    instance_id: int,
    user: CurrentUser,
    session: DbSession,
) -> WorkflowInstanceRead:
    return await InstanceService(session).get_instance(user, instance_id)


@router.get(
    "/{instance_id}/events",
    response_model=list[WorkflowEventRead],
    summary="Read append-only workflow history",
    description="Events are ordered by `sequence` per instance (audit trail).",
)
async def list_instance_events(
    instance_id: int,
    user: CurrentUser,
    session: DbSession,
) -> list[WorkflowEventRead]:
    return await InstanceService(session).list_events(user, instance_id)


@router.post(
    "",
    response_model=WorkflowInstanceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start a workflow instance",
)
async def start_instance(
    user: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: Annotated[InstanceStart, Body(openapi_examples=_START_EXAMPLES)],
) -> WorkflowInstanceRead:
    return await InstanceService(session).start_instance(
        user,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{instance_id}/transitions",
    response_model=WorkflowInstanceRead,
    summary="Fire a workflow action",
    description=(
        "Validates the action against the definition graph and the instance's "
        "current state. Requires **Idempotency-Key**."
    ),
)
async def transition_instance(
    instance_id: int,
    user: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: Annotated[TransitionCommand, Body(openapi_examples=_TRANSITION_EXAMPLES)],
) -> WorkflowInstanceRead:
    return await InstanceService(session).transition(
        user,
        instance_id,
        payload,
        idempotency_key=idempotency_key,
    )
