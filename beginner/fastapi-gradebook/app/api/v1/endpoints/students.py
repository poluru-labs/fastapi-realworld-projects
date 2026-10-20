from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_gradebook_service
from app.schemas.gradebook import (
    StudentCreate,
    StudentDeleteResponse,
    StudentRead,
    StudentReport,
    StudentUpdate,
)
from app.services.gradebook_service import GradebookService

router = APIRouter()


@router.get("", response_model=list[StudentRead], summary="List students")
def list_students(
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> list[StudentRead]:
    return service.list_students()


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> StudentRead:
    return service.create_student(payload)


@router.get("/{student_id}", response_model=StudentRead, summary="Get student")
def get_student(
    student_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> StudentRead:
    return service.get_student(student_id)


@router.patch("/{student_id}", response_model=StudentRead, summary="Update student")
def update_student(
    student_id: int,
    payload: StudentUpdate,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> StudentRead:
    return service.update_student(student_id, payload)


@router.get(
    "/{student_id}/report",
    response_model=StudentReport,
    summary="Student grade summary",
    description="Averages **final** grade percentages across all courses.",
)
def student_report(
    student_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> StudentReport:
    return service.student_report(student_id)


@router.delete("/{student_id}", response_model=StudentDeleteResponse)
def delete_student(
    student_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> StudentDeleteResponse:
    return service.delete_student(student_id)
