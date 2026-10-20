from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_gradebook_service
from app.schemas.gradebook import (
    GradeCategory,
    GradeDeleteResponse,
    GradeRead,
    GradeStatus,
    GradeUpdate,
)
from app.services.gradebook_service import GradebookService

router = APIRouter()


@router.get(
    "",
    response_model=list[GradeRead],
    summary="List grades",
    description=(
        "By default only **final** grades are returned. "
        "Pass `include_draft=true` or `status=draft` to include drafts."
    ),
)
def list_grades(
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
    course_id: Annotated[int | None, Query(ge=1)] = None,
    student_id: Annotated[int | None, Query(ge=1)] = None,
    category: Annotated[GradeCategory | None, Query()] = None,
    grade_status: Annotated[GradeStatus | None, Query(alias="status")] = None,
    include_draft: Annotated[bool, Query()] = False,
) -> list[GradeRead]:
    return service.list_grades(
        course_id=course_id,
        student_id=student_id,
        category=category,
        status=grade_status,
        include_draft=include_draft or grade_status is GradeStatus.DRAFT,
    )


@router.get("/{grade_id}", response_model=GradeRead, summary="Get grade")
def get_grade(
    grade_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> GradeRead:
    return service.get_grade(grade_id)


@router.patch("/{grade_id}", response_model=GradeRead, summary="Update draft grade")
def update_grade(
    grade_id: int,
    payload: GradeUpdate,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> GradeRead:
    return service.update_grade(grade_id, payload)


@router.post("/{grade_id}/finalize", response_model=GradeRead, summary="Finalize grade")
def finalize_grade(
    grade_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> GradeRead:
    return service.finalize_grade(grade_id)


@router.post("/{grade_id}/reopen", response_model=GradeRead, summary="Reopen final grade")
def reopen_grade(
    grade_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> GradeRead:
    return service.reopen_grade(grade_id)


@router.delete("/{grade_id}", response_model=GradeDeleteResponse)
def delete_grade(
    grade_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> GradeDeleteResponse:
    return service.delete_grade(grade_id)
