from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator


class GradeCategory(StrEnum):
    EXAM = "exam"
    HOMEWORK = "homework"
    PROJECT = "project"
    PARTICIPATION = "participation"


class GradeStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


def _normalize_code(value: str) -> str:
    return value.strip().upper()


class StudentCreate(BaseModel):
    student_number: str = Field(..., min_length=2, max_length=32)
    full_name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr | None = None

    @field_validator("student_number", mode="before")
    @classmethod
    def normalize_student_number(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_code(value)
        return value

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_number: str
    full_name: str
    email: EmailStr | None
    created_at: datetime


class StudentDeleteResponse(BaseModel):
    deleted: bool = True
    id: int


class CourseCreate(BaseModel):
    course_code: str = Field(..., min_length=2, max_length=32)
    title: str = Field(..., min_length=1, max_length=120)
    term: str = Field(..., min_length=1, max_length=32)

    @field_validator("course_code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_code(value)
        return value

    @field_validator("title", "term", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    term: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("title", "term", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_code: str
    title: str
    term: str
    created_at: datetime


class EnrollmentCreate(BaseModel):
    student_id: int = Field(ge=1)


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime


class GradeCreate(BaseModel):
    student_id: int = Field(ge=1)
    title: str = Field(..., min_length=1, max_length=120)
    category: GradeCategory = GradeCategory.HOMEWORK
    points_earned: float = Field(..., ge=0)
    points_possible: float = Field(..., gt=0)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class GradeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    category: GradeCategory | None = None
    points_earned: float | None = Field(default=None, ge=0)
    points_possible: float | None = Field(default=None, gt=0)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class GradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    student_id: int
    title: str
    category: GradeCategory
    points_earned: float
    points_possible: float
    status: GradeStatus
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def percentage(self) -> float:
        if self.points_possible <= 0:
            return 0.0
        return round(100.0 * self.points_earned / self.points_possible, 2)


class GradeDeleteResponse(BaseModel):
    deleted: bool = True
    id: int


class StudentReport(BaseModel):
    student_id: int
    final_grade_count: int
    average_percentage: float | None = Field(
        description="Mean percentage across **final** grades only; null if none."
    )
