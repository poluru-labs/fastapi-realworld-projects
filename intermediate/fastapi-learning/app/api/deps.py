from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories.course_repository import CourseRepository, LessonRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserRole
from app.services.auth_service import AuthService
from app.services.course_service import CourseService
from app.services.enrollment_service import EnrollmentService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()


@lru_cache
def get_refresh_token_repository() -> RefreshTokenRepository:
    return RefreshTokenRepository()


@lru_cache
def get_course_repository() -> CourseRepository:
    return CourseRepository()


@lru_cache
def get_lesson_repository() -> LessonRepository:
    return LessonRepository()


@lru_cache
def get_enrollment_repository() -> EnrollmentRepository:
    return EnrollmentRepository()


def get_auth_service(
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:
    return AuthService(settings=settings, users=users, refresh_tokens=refresh_tokens)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


def get_course_service(
    courses: Annotated[CourseRepository, Depends(get_course_repository)],
    lessons: Annotated[LessonRepository, Depends(get_lesson_repository)],
    enrollments: Annotated[EnrollmentRepository, Depends(get_enrollment_repository)],
) -> CourseService:
    return CourseService(courses=courses, lessons=lessons, enrollments=enrollments)


def get_enrollment_service(
    courses: Annotated[CourseRepository, Depends(get_course_repository)],
    lessons: Annotated[LessonRepository, Depends(get_lesson_repository)],
    enrollments: Annotated[EnrollmentRepository, Depends(get_enrollment_repository)],
) -> EnrollmentService:
    return EnrollmentService(courses=courses, lessons=lessons, enrollments=enrollments)


def _user_from_access_token(token: str, settings: Settings, users: UserRepository) -> UserRead:
    payload = decode_token(settings=settings, token=token, expected_type="access")
    user_id = int(payload["sub"])
    record = users.get_by_id(user_id)
    if record is None or not record.is_active:
        raise UnauthorizedError()
    return record.to_read()


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    return _user_from_access_token(token, settings, users)


def get_optional_user(
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> UserRead | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError()
    return _user_from_access_token(token, settings, users)


def require_roles(*allowed: UserRole) -> Callable[..., UserRead]:
    def checker(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
        if current_user.role not in allowed:
            raise ForbiddenError()
        return current_user

    return checker
