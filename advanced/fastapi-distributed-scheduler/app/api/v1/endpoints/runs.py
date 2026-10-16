from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.scheduler import ScheduledRunRead
from app.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/mine", response_model=list[ScheduledRunRead], summary="List your runs")
async def list_my_runs(
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScheduledRunRead]:
    return await RunService(session, settings).list_mine(user, limit=limit, offset=offset)


@router.get("/{run_id}", response_model=ScheduledRunRead, summary="Get a run you own")
async def get_run(
    run_id: int,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> ScheduledRunRead:
    return await RunService(session, settings).get_run(user, run_id)


@router.post("/{run_id}/cancel", response_model=ScheduledRunRead, summary="Cancel pending/running")
async def cancel_run(
    run_id: int,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUser,
) -> ScheduledRunRead:
    return await RunService(session, settings).cancel(user, run_id)
