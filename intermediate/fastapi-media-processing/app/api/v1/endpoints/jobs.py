from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_media_service, require_roles
from app.schemas.media import JobRead, JobSubmit, OperationCatalogEntry
from app.schemas.user import UserRead, UserRole
from app.services.media_service import MediaService

router = APIRouter()

AdminUser = Annotated[UserRead, Depends(require_roles(UserRole.ADMIN))]


@router.get(
    "/operations",
    response_model=list[OperationCatalogEntry],
    summary="Processing operations catalog",
    description="Admin only. Documents allowed media kinds and parameter shapes.",
)
def list_operations(
    admin: AdminUser,
    service: Annotated[MediaService, Depends(get_media_service)],
) -> list[OperationCatalogEntry]:
    return service.list_operations(admin)


@router.get(
    "",
    response_model=list[JobRead],
    summary="List my processing jobs",
    description="Newest first. Each job stores simulated output metadata when completed.",
)
def list_jobs(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> list[JobRead]:
    return service.list_jobs(current_user)


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a processing job",
    description=(
        "Runs synchronously and returns a **completed** or **failed** job. "
        "Use either `preset_id` or inline `operation` + `parameters`, not both."
    ),
)
def submit_job(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    payload: JobSubmit,
) -> JobRead:
    return service.submit_job(current_user, payload)


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Get one processing job",
    description="Returns **404** for another user's job id.",
)
def get_job(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    job_id: int,
) -> JobRead:
    return service.get_job(current_user, job_id)
