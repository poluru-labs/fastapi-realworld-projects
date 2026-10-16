from typing import Annotated

from fastapi import APIRouter, Body

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.scheduler import (
    ClaimRunRequest,
    CompleteRunRequest,
    ScheduledRunRead,
    WorkerHeartbeat,
    WorkerRegister,
)
from app.services.run_service import RunService

router = APIRouter(prefix="/workers", tags=["workers"])

_REGISTER_EXAMPLES = {
    "report_worker": {
        "summary": "Worker that handles report tasks",
        "value": {"worker_id": "worker-a", "capabilities": ["report", "sync"]},
    }
}


@router.post(
    "/register",
    summary="Register a worker identity",
    description="Capabilities filter which pending runs this worker may claim.",
)
async def register_worker(
    payload: Annotated[WorkerRegister, Body(openapi_examples=_REGISTER_EXAMPLES)],
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> dict[str, str]:
    return await RunService(session, settings).register_worker(user, payload)


@router.post("/heartbeat", summary="Refresh worker liveness")
async def worker_heartbeat(
    payload: WorkerHeartbeat,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> dict[str, str]:
    return await RunService(session, settings).heartbeat(user, payload)


@router.post(
    "/claim",
    response_model=ScheduledRunRead,
    summary="Claim the next runnable job",
    description=(
        "Finds the oldest **pending** run matching the worker capabilities whose lease "
        "is free or expired. Sets status to **running** and grants a lease."
    ),
)
async def claim_run(
    payload: ClaimRunRequest,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> ScheduledRunRead:
    return await RunService(session, settings).claim(user, payload)


@router.post(
    "/runs/{run_id}/complete",
    response_model=ScheduledRunRead,
    summary="Finish a leased run",
    description=(
        "Requires matching **worker_id**, valid lease, and **expected_version**. "
        "Failures may re-queue until `max_attempts` is exhausted."
    ),
)
async def complete_run(
    run_id: int,
    payload: CompleteRunRequest,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> ScheduledRunRead:
    return await RunService(session, settings).complete(user, run_id, payload)
