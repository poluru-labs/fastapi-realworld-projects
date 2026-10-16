from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_application_service, get_current_user
from app.schemas.application import ApplicationCreate, ApplicationPage, ApplicationRead
from app.schemas.job import SLUG_PATTERN
from app.schemas.user import UserRead
from app.services.application_service import ApplicationService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        examples=["senior-fastapi-engineer"],
    ),
]

_CREATE_EXAMPLES = {
    "cover_letter": {
        "summary": "Apply with a short note",
        "value": {
            "cover_letter": "I have shipped FastAPI services in production for three years.",
        },
    }
}


@router.get(
    "",
    response_model=ApplicationPage,
    summary="List applications for a job",
    description=(
        "Employer or admin only. You must be able to see the job (including drafts you own)."
    ),
)
def list_applications_for_job(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApplicationPage:
    return service.list_for_job(actor, slug, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a published job",
    description=(
        "Signed-in users only. Job must be `published`. You cannot apply to your own posting. "
        "Re-applying after withdraw updates the same row."
    ),
)
def apply_to_job(
    slug: Slug,
    payload: Annotated[ApplicationCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
) -> ApplicationRead:
    return service.apply(actor, slug, payload)


@router.post(
    "/{application_id}/withdraw",
    response_model=ApplicationRead,
    summary="Withdraw your application",
)
def withdraw_application(
    slug: Slug,
    application_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
) -> ApplicationRead:
    return service.withdraw(actor, slug, application_id)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
    description="Applicant, employer for that job, or platform admin.",
)
def delete_application(
    slug: Slug,
    application_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
) -> None:
    service.delete_application(actor, slug, application_id)
