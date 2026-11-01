from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_monitor_service
from app.schemas.monitor import CheckResultRead, MonitorCreate, MonitorRead, MonitorUpdate
from app.schemas.user import UserRead
from app.services.monitor_service import MonitorService

router = APIRouter()


@router.get(
    "",
    response_model=list[MonitorRead],
    summary="List monitors",
    description="Owners see their monitors. Platform admins see every monitor.",
)
def list_monitors(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> list[MonitorRead]:
    return service.list_monitors(current_user)


@router.post(
    "",
    response_model=MonitorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a monitor",
    description=(
        "Targets are probed by a mock HTTP client (no real outbound traffic). "
        "Set `is_public` to expose `/api/v1/status/{slug}`."
    ),
)
def create_monitor(
    payload: MonitorCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> MonitorRead:
    return service.create_monitor(current_user, payload)


@router.get(
    "/{slug}",
    response_model=MonitorRead,
    summary="Read monitor metadata",
)
def get_monitor(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> MonitorRead:
    return service.get_monitor(current_user, slug)


@router.patch(
    "/{slug}",
    response_model=MonitorRead,
    summary="Update a monitor",
)
def update_monitor(
    slug: str,
    payload: MonitorUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> MonitorRead:
    return service.update_monitor(current_user, slug, payload)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a monitor",
)
def delete_monitor(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> None:
    service.delete_monitor(current_user, slug)


@router.post(
    "/{slug}/pause",
    response_model=MonitorRead,
    summary="Pause checks",
    responses={409: {"description": "Already paused."}},
)
def pause_monitor(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> MonitorRead:
    return service.pause_monitor(current_user, slug)


@router.post(
    "/{slug}/resume",
    response_model=MonitorRead,
    summary="Resume checks",
)
def resume_monitor(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> MonitorRead:
    return service.resume_monitor(current_user, slug)


@router.post(
    "/{slug}/checks",
    response_model=CheckResultRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run a probe now",
    description="Executes the mock probe asynchronously and stores the result.",
    responses={409: {"description": "Monitor is paused."}},
)
async def run_check(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> CheckResultRead:
    return await service.run_check(current_user, slug)


@router.get(
    "/{slug}/checks",
    response_model=list[CheckResultRead],
    summary="Check history",
)
def list_checks(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MonitorService, Depends(get_monitor_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CheckResultRead]:
    return service.list_checks(current_user, slug, limit=limit)
