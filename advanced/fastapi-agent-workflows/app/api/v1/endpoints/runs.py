from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminKey, DbSession, IdempotencyKey, RunnerKey, RunnerOrAdmin
from app.schemas.agent_workflow import RunCreate, RunRead
from app.services.agent_workflow_service import AgentWorkflowService

router = APIRouter()


@router.post(
    "",
    response_model=RunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an agent workflow",
    description=(
        "Requires **X-Runner-Key** and **Idempotency-Key**. Runs steps synchronously, "
        "appends per-step logs, and stores final context. Replace mock agent/tool handlers "
        "with real LLM and MCP calls in production."
    ),
)
async def start_run(
    _: RunnerKey,
    session: DbSession,
    payload: RunCreate,
    idempotency_key: IdempotencyKey,
) -> RunRead:
    return await AgentWorkflowService(session).create_run(payload, idempotency_key=idempotency_key)


@router.get(
    "",
    response_model=list[RunRead],
    summary="List agent runs",
    description="Admin audit feed, newest first.",
)
async def list_runs(
    _: AdminKey,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RunRead]:
    return await AgentWorkflowService(session).list_runs(limit=limit, offset=offset)


@router.get(
    "/{run_id}",
    response_model=RunRead,
    summary="Get run detail with step logs",
)
async def get_run(
    _: RunnerOrAdmin,
    session: DbSession,
    run_id: Annotated[int, Path(ge=1)],
) -> RunRead:
    return await AgentWorkflowService(session).get_run(run_id)
