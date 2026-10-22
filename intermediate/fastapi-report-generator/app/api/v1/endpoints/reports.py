from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_report_service, require_roles
from app.schemas.report import MetricRead, ReportGenerate, ReportRunRead
from app.schemas.user import UserRead, UserRole
from app.services.report_service import ReportService

router = APIRouter()

AdminUser = Annotated[UserRead, Depends(require_roles(UserRole.ADMIN))]


@router.get(
    "/metrics",
    response_model=list[MetricRead],
    summary="Metrics source catalog",
    description="Admin only. Raw rows used when generating reports.",
)
def list_metrics(
    admin: AdminUser,
    service: Annotated[ReportService, Depends(get_report_service)],
) -> list[MetricRead]:
    return service.list_metrics(admin)


@router.get(
    "/runs",
    response_model=list[ReportRunRead],
    summary="List my report runs",
    description="Newest first. Each run stores the computed JSON result.",
)
def list_runs(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
) -> list[ReportRunRead]:
    return service.list_runs(current_user)


@router.post(
    "/runs",
    response_model=ReportRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a report",
    description=(
        "Loads the template kind, aggregates metrics in `[period_start, period_end]`, "
        "and stores a **completed** run with structured sections."
    ),
)
def generate_report(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    payload: ReportGenerate,
) -> ReportRunRead:
    return service.generate(current_user, payload)


@router.get(
    "/runs/{run_id}",
    response_model=ReportRunRead,
    summary="Get one report run",
    description="Returns **404** for another user's run id.",
)
def get_run(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    run_id: int,
) -> ReportRunRead:
    return service.get_run(current_user, run_id)
