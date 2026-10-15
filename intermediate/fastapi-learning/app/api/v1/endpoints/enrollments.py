from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_enrollment_service
from app.schemas.course import EnrollmentCreate, EnrollmentRead, EnrollmentStatus
from app.schemas.user import UserRead
from app.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

_ENROLL_EXAMPLES = {
    "fundamentals": {
        "summary": "Enroll in the seed course",
        "value": {"course_slug": "fastapi-fundamentals"},
    }
}


@router.get(
    "",
    response_model=list[EnrollmentRead],
    summary="List enrollments",
    description="Students see their rows. Platform admins see every enrollment.",
)
def list_enrollments(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EnrollmentService, Depends(get_enrollment_service)],
    enrollment_status: Annotated[EnrollmentStatus | None, Query(alias="status")] = None,
) -> list[EnrollmentRead]:
    return service.list_enrollments(actor, status=enrollment_status)


@router.get("/{enrollment_id}", response_model=EnrollmentRead, summary="Get one enrollment")
def get_enrollment(
    enrollment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EnrollmentService, Depends(get_enrollment_service)],
) -> EnrollmentRead:
    return service.get_enrollment(actor, enrollment_id)


@router.post(
    "",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in a published course",
)
def enroll(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EnrollmentService, Depends(get_enrollment_service)],
    payload: Annotated[EnrollmentCreate, Body(openapi_examples=_ENROLL_EXAMPLES)],
) -> EnrollmentRead:
    return service.enroll(actor, payload)


@router.post(
    "/{enrollment_id}/lessons/{lesson_slug}/complete",
    response_model=EnrollmentRead,
    summary="Mark a lesson complete",
    description="When every **published** lesson is done, enrollment status becomes **completed**.",
)
def complete_lesson(
    enrollment_id: int,
    lesson_slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EnrollmentService, Depends(get_enrollment_service)],
) -> EnrollmentRead:
    return service.complete_lesson(actor, enrollment_id, lesson_slug)


@router.post(
    "/{enrollment_id}/drop",
    response_model=EnrollmentRead,
    summary="Drop an active enrollment",
)
def drop_enrollment(
    enrollment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EnrollmentService, Depends(get_enrollment_service)],
) -> EnrollmentRead:
    return service.drop(actor, enrollment_id)
