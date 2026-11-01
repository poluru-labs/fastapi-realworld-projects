from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminKey, DbSession, IdempotencyKey, RunnerKey, RunnerOrAdmin
from app.schemas.execution import RunCreate, RunRead
from app.services.execution_service import ExecutionService

router = APIRouter()


@router.post(
    "",
    response_model=RunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for sandbox execution",
    description=(
        "Requires **X-Runner-Key** and **Idempotency-Key**. Source is validated with AST "
        "rules (no imports, restricted builtins), then executed in a thread pool with "
        "asyncio timeout. This is **not** a production-grade isolation boundary."
    ),
)
async def create_run(
    _: RunnerKey,
    session: DbSession,
    payload: RunCreate,
    idempotency_key: IdempotencyKey,
) -> RunRead:
    return await ExecutionService(session).create_run(payload, idempotency_key=idempotency_key)


@router.get(
    "",
    response_model=list[RunRead],
    summary="List recent runs",
    description="Admin-only audit view. Newest runs first.",
)
async def list_runs(
    _: AdminKey,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RunRead]:
    return await ExecutionService(session).list_runs(limit=limit, offset=offset)


@router.get(
    "/{run_id}",
    response_model=RunRead,
    summary="Fetch a run by id",
    description="Runner or admin key may read a stored run (including rejected submissions).",
)
async def get_run(
    _: RunnerOrAdmin,
    session: DbSession,
    run_id: Annotated[int, Path(ge=1)],
) -> RunRead:
    return await ExecutionService(session).get_run(run_id)
