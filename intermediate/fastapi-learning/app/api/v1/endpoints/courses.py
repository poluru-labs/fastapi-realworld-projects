from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_course_service, get_current_user, get_optional_user
from app.schemas.course import (
    CourseCreate,
    CourseLevel,
    CourseRead,
    CourseStatus,
    CourseUpdate,
    LessonCreate,
    LessonRead,
    LessonUpdate,
)
from app.schemas.user import UserRead
from app.services.course_service import CourseService

router = APIRouter()

_CREATE_EXAMPLES = {
    "course": {
        "summary": "New draft course",
        "value": {
            "title": "Testing FastAPI",
            "summary": "Pytest and TestClient patterns.",
            "level": "intermediate",
        },
    }
}


@router.get(
    "/courses",
    response_model=list[CourseRead],
    summary="List courses",
    description="Guests see **published** courses. Admins may filter `status` and `level`.",
)
def list_courses(
    service: Annotated[CourseService, Depends(get_course_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    course_status: Annotated[CourseStatus | None, Query(alias="status")] = None,
    level: Annotated[CourseLevel | None, Query()] = None,
) -> list[CourseRead]:
    return service.list_courses(actor, status=course_status, level=level)


@router.get("/courses/{slug}", response_model=CourseRead, summary="Get one course")
def get_course(
    slug: str,
    service: Annotated[CourseService, Depends(get_course_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> CourseRead:
    return service.get_course(actor, slug)


@router.post(
    "/courses",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft course (admin)",
)
def create_course(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
    payload: Annotated[CourseCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> CourseRead:
    return service.create_course(actor, payload)


@router.patch("/courses/{slug}", response_model=CourseRead, summary="Update draft course")
def update_course(
    slug: str,
    payload: CourseUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> CourseRead:
    return service.update_course(actor, slug, payload)


@router.post("/courses/{slug}/publish", response_model=CourseRead, summary="Publish course")
def publish_course(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> CourseRead:
    return service.transition_course(actor, slug, CourseStatus.PUBLISHED)


@router.post("/courses/{slug}/archive", response_model=CourseRead, summary="Archive course")
def archive_course(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> CourseRead:
    return service.transition_course(actor, slug, CourseStatus.ARCHIVED)


@router.get(
    "/courses/{course_slug}/lessons",
    response_model=list[LessonRead],
    summary="List lessons in a course",
    description=(
        "Lesson **body** is empty until you enroll (or you are admin). "
        "Draft lessons return **404** to guests."
    ),
)
def list_lessons(
    course_slug: str,
    service: Annotated[CourseService, Depends(get_course_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> list[LessonRead]:
    return service.list_lessons(actor, course_slug)


@router.get(
    "/courses/{course_slug}/lessons/{lesson_slug}",
    response_model=LessonRead,
    summary="Get one lesson",
)
def get_lesson(
    course_slug: str,
    lesson_slug: str,
    service: Annotated[CourseService, Depends(get_course_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> LessonRead:
    return service.get_lesson(actor, course_slug, lesson_slug)


@router.post(
    "/courses/{course_slug}/lessons",
    response_model=LessonRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a draft lesson (admin)",
)
def create_lesson(
    course_slug: str,
    payload: LessonCreate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> LessonRead:
    return service.create_lesson(actor, course_slug, payload)


@router.patch(
    "/courses/{course_slug}/lessons/{lesson_slug}",
    response_model=LessonRead,
    summary="Update draft lesson (admin)",
)
def update_lesson(
    course_slug: str,
    lesson_slug: str,
    payload: LessonUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> LessonRead:
    return service.update_lesson(actor, course_slug, lesson_slug, payload)


@router.post(
    "/courses/{course_slug}/lessons/{lesson_slug}/publish",
    response_model=LessonRead,
    summary="Publish lesson (admin)",
)
def publish_lesson(
    course_slug: str,
    lesson_slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> LessonRead:
    return service.publish_lesson(actor, course_slug, lesson_slug)


@router.post(
    "/courses/{course_slug}/lessons/{lesson_slug}/unpublish",
    response_model=LessonRead,
    summary="Return lesson to draft (admin)",
)
def unpublish_lesson(
    course_slug: str,
    lesson_slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CourseService, Depends(get_course_service)],
) -> LessonRead:
    return service.unpublish_lesson(actor, course_slug, lesson_slug)
