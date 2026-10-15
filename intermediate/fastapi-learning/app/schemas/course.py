import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")


class CourseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CourseLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LessonStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class EnrollmentStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


class CourseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    summary: str = Field(default="", max_length=800)
    level: CourseLevel = CourseLevel.INTERMEDIATE

    @model_validator(mode="after")
    def validate_slug(self) -> "CourseCreate":
        if self.slug is not None and not SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens")
        return self


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=800)
    level: CourseLevel | None = None


class CourseRead(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    level: CourseLevel
    status: CourseStatus
    published_lesson_count: int
    created_at: datetime
    updated_at: datetime


class LessonCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    body: str = Field(default="", max_length=20_000)
    sort_order: int = Field(default=0, ge=0, le=9999)

    @model_validator(mode="after")
    def validate_slug(self) -> "LessonCreate":
        if self.slug is not None and not SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens")
        return self


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=20_000)
    sort_order: int | None = Field(default=None, ge=0, le=9999)


class LessonRead(BaseModel):
    id: int
    course_id: int
    course_slug: str
    slug: str
    title: str
    body: str = Field(description="Empty when the caller is not enrolled (and not admin).")
    sort_order: int
    status: LessonStatus
    created_at: datetime
    updated_at: datetime


class EnrollmentCreate(BaseModel):
    course_slug: str = Field(min_length=1, max_length=80)


class EnrollmentRead(BaseModel):
    id: int
    user_id: int
    course_id: int
    course_slug: str
    course_title: str
    status: EnrollmentStatus
    completed_lessons: int
    total_lessons: int
    progress_percent: int
    enrolled_at: datetime
    completed_at: datetime | None
