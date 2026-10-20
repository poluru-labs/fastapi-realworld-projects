from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.api.deps import get_gradebook_service
from app.schemas.gradebook import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    EnrollmentCreate,
    EnrollmentRead,
    GradeCreate,
    GradeRead,
)
from app.services.gradebook_service import GradebookService

router = APIRouter()

_CREATE_EXAMPLES = {
    "intro": {
        "summary": "Spring term course",
        "value": {
            "course_code": "CS201",
            "title": "Data structures",
            "term": "Spring 2026",
        },
    }
}


@router.get("", response_model=list[CourseRead], summary="List courses")
def list_courses(
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> list[CourseRead]:
    return service.list_courses()


@router.post(
    "",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create course",
)
def create_course(
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
    payload: Annotated[CourseCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> CourseRead:
    return service.create_course(payload)


@router.get("/{course_id}", response_model=CourseRead, summary="Get course")
def get_course(
    course_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> CourseRead:
    return service.get_course(course_id)


@router.patch("/{course_id}", response_model=CourseRead, summary="Update course")
def update_course(
    course_id: int,
    payload: CourseUpdate,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> CourseRead:
    return service.update_course(course_id, payload)


@router.get(
    "/{course_id}/enrollments",
    response_model=list[EnrollmentRead],
    summary="List enrollments in a course",
)
def list_enrollments(
    course_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> list[EnrollmentRead]:
    return service.list_enrollments(course_id)


@router.post(
    "/{course_id}/enrollments",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student",
    description="Returns **409** if the student is already enrolled.",
)
def enroll_student(
    course_id: int,
    payload: EnrollmentCreate,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
) -> EnrollmentRead:
    return service.enroll(course_id, payload)


_GRADE_EXAMPLES = {
    "homework": {
        "summary": "Draft homework score",
        "value": {
            "student_id": 1,
            "title": "Problem set 4",
            "category": "homework",
            "points_earned": 18,
            "points_possible": 20,
        },
    }
}


@router.post(
    "/{course_id}/grades",
    response_model=GradeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a draft grade",
    description="Student must be enrolled. New grades start as **draft**.",
)
def create_grade(
    course_id: int,
    service: Annotated[GradebookService, Depends(get_gradebook_service)],
    payload: Annotated[GradeCreate, Body(openapi_examples=_GRADE_EXAMPLES)],
) -> GradeRead:
    return service.create_grade(course_id, payload)
