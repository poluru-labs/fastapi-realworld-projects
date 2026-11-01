from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.agent_workflow import (
    SLUG_PATTERN,
    WorkflowDefinitionCreate,
    WorkflowDefinitionRead,
    WorkflowDefinitionUpdate,
)
from app.services.agent_workflow_service import AgentWorkflowService

router = APIRouter()

WorkflowSlug = Annotated[
    str,
    Path(pattern=SLUG_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[WorkflowDefinitionRead],
    summary="List agent workflow definitions",
    description="Admin-only catalog of draft and published DAG-style step lists.",
)
async def list_workflows(_: AdminKey, session: DbSession) -> list[WorkflowDefinitionRead]:
    return await AgentWorkflowService(session).list_definitions()


@router.post(
    "",
    response_model=WorkflowDefinitionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft workflow",
    description=(
        "Steps are an ordered list of **agent** (prompt template) and **tool** (mock tool) nodes. "
        "Validate graph shape in Pydantic before persisting JSON."
    ),
)
async def create_workflow(
    _: AdminKey,
    session: DbSession,
    payload: WorkflowDefinitionCreate,
) -> WorkflowDefinitionRead:
    return await AgentWorkflowService(session).create_definition(payload)


@router.get(
    "/{workflow_slug}",
    response_model=WorkflowDefinitionRead,
    summary="Get workflow definition",
)
async def get_workflow(
    _: AdminKey,
    session: DbSession,
    workflow_slug: WorkflowSlug,
) -> WorkflowDefinitionRead:
    return await AgentWorkflowService(session).get_definition(workflow_slug)


@router.patch(
    "/{workflow_slug}",
    response_model=WorkflowDefinitionRead,
    summary="Update draft workflow",
    description="Published workflows are immutable; publish a new version in production systems.",
)
async def update_workflow(
    _: AdminKey,
    session: DbSession,
    workflow_slug: WorkflowSlug,
    payload: WorkflowDefinitionUpdate,
) -> WorkflowDefinitionRead:
    return await AgentWorkflowService(session).update_definition(workflow_slug, payload)


@router.post(
    "/{workflow_slug}/publish",
    response_model=WorkflowDefinitionRead,
    summary="Publish workflow",
    description="Only published workflows accept runner executions.",
)
async def publish_workflow(
    _: AdminKey,
    session: DbSession,
    workflow_slug: WorkflowSlug,
) -> WorkflowDefinitionRead:
    return await AgentWorkflowService(session).publish_definition(workflow_slug)
