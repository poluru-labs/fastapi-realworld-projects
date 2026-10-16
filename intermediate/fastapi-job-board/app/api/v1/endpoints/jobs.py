from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_current_user, get_job_service, get_optional_user
from app.schemas.job import (
    SLUG_PATTERN,
    JobCreate,
    JobPage,
    JobRead,
    JobStatus,
    JobUpdate,
    WorkMode,
)
from app.schemas.user import UserRead
from app.services.job_service import JobService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        description="Lowercase words separated by hyphens.",
        examples=["senior-fastapi-engineer"],
    ),
]

_OPTIONAL_BEARER = {"security": [{}, {"OAuth2PasswordBearer": []}]}

_CREATE_EXAMPLES = {
    "from_title": {
        "summary": "Draft job, slug from title",
        "description": "Stays draft until POST .../publish.",
        "value": {
            "title": "Backend engineer",
            "company": "Acme Labs",
            "summary": "Ship APIs with clear auth boundaries.",
            "description": "Design REST services and mentor juniors.",
            "location": "Remote",
            "work_mode": "remote",
            "employment_type": "full_time",
            "skills": ["python", "fastapi"],
        },
    },
    "custom_slug": {
        "summary": "Draft with explicit slug",
        "value": {
            "title": "Backend engineer",
            "company": "Acme Labs",
            "description": "Second opening with the same title.",
            "slug": "backend-engineer-contract",
            "employment_type": "contract",
        },
    },
}


@router.get(
    "",
    response_model=JobPage,
    summary="List published jobs",
    description=(
        "Public board. Drafts and closed jobs never appear here. Filters combine with AND. "
        "`q` matches title, company, summary, description, and location. "
        "Newest `published_at` first."
    ),
)
def list_jobs(
    service: Annotated[JobService, Depends(get_job_service)],
    skill: Annotated[
        str | None,
        Query(max_length=32, description="Keep jobs that include this skill.", examples=["python"]),
    ] = None,
    employer_id: Annotated[
        int | None,
        Query(ge=1, description="Keep jobs posted by this user id."),
    ] = None,
    work_mode: Annotated[
        WorkMode | None,
        Query(description="Filter by remote, hybrid, or onsite."),
    ] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=80, description="Case-insensitive search."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobPage:
    return service.list_published(
        skill=skill,
        employer_id=employer_id,
        work_mode=work_mode.value if work_mode else None,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/mine",
    response_model=JobPage,
    summary="List jobs you posted",
    description="All statuses you own. Admins do not see other employers' drafts here.",
)
def list_my_jobs(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
    job_status: Annotated[
        JobStatus | None,
        Query(alias="status", description="Filter by job status."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobPage:
    return service.list_mine(actor, status=job_status, limit=limit, offset=offset)


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft job",
    description=(
        "Any signed-in user can post. New jobs start as `draft`. Slugs are unique and immutable."
    ),
)
def create_job(
    payload: Annotated[JobCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.create_job(actor, payload)


@router.get(
    "/{slug}",
    response_model=JobRead,
    summary="Get one job",
    description=(
        "Published jobs need no token. Send a valid token to preview your draft or closed posting, "
        "or any job as admin. Hidden jobs return **404**; invalid tokens return **401**."
    ),
    openapi_extra=_OPTIONAL_BEARER,
)
def get_job(
    slug: Slug,
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.get_job(actor, slug)


@router.patch(
    "/{slug}",
    response_model=JobRead,
    summary="Edit your job",
    description="Employer only. Admins can read and close jobs but cannot rewrite descriptions.",
)
def update_job(
    slug: Slug,
    payload: JobUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.update_job(actor, slug, payload)


@router.post(
    "/{slug}/publish",
    response_model=JobRead,
    summary="Publish a draft",
    description="Employer only. Legal move: `draft` → `published`. Sets `published_at` to now.",
)
def publish_job(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.publish(actor, slug)


@router.post("/{slug}/unpublish", response_model=JobRead, summary="Return a published job to draft")
def unpublish_job(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.unpublish(actor, slug)


@router.post(
    "/{slug}/close",
    response_model=JobRead,
    summary="Close a published job",
    description="Employer or admin. Legal move: `published` → `closed`. Stops new applications.",
)
def close_job(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.close(actor, slug)


@router.post(
    "/{slug}/reopen",
    response_model=JobRead,
    summary="Reopen a closed job to draft",
    description="Employer only. Legal move: `closed` → `draft`. Publish again when ready.",
)
def reopen_job(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRead:
    return service.reopen(actor, slug)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job",
    description="Employer or admin. Applications are deleted with the job.",
)
def delete_job(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> None:
    service.delete_job(actor, slug)
