import re
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_SKILL_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class JobStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


def slugify(value: str) -> str:
    """Turn a title into a URL slug. Empty when the title has no letters or digits."""
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


def normalize_skills(skills: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in skills:
        skill = raw.strip().casefold()
        if not _SKILL_PATTERN.fullmatch(skill) or len(skill) > 32:
            raise ValueError(
                "Skills must be lowercase words, optionally hyphenated, up to 32 characters"
            )
        if skill not in seen:
            seen.add(skill)
            cleaned.append(skill)
    return cleaned


class JobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=120,
        examples=["Senior FastAPI Engineer"],
    )
    company: str = Field(..., min_length=1, max_length=80, examples=["Acme Labs"])
    summary: str = Field(
        default="",
        max_length=280,
        description="Short blurb for the public job board.",
    )
    description: str = Field(..., min_length=1, max_length=20_000)
    location: str = Field(default="Remote", max_length=80)
    work_mode: WorkMode = WorkMode.REMOTE
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    salary_min: int | None = Field(default=None, ge=0, description="Optional lower bound (USD).")
    salary_max: int | None = Field(default=None, ge=0, description="Optional upper bound (USD).")
    skills: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Up to 8 skills. Case is ignored and duplicates are dropped.",
        examples=[["python", "fastapi"]],
    )
    slug: str | None = Field(
        default=None,
        max_length=80,
        description="Public URL id. Omit to derive from the title. Never changes after create.",
        examples=["senior-fastapi-engineer"],
    )

    @field_validator("slug")
    @classmethod
    def check_slug(cls, slug: str | None) -> str | None:
        if slug is None:
            return None
        slug = slug.strip().casefold()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return slug

    @field_validator("skills")
    @classmethod
    def check_skills(cls, skills: list[str]) -> list[str]:
        return normalize_skills(skills)

    @model_validator(mode="after")
    def title_can_slugify(self) -> Self:
        if self.slug is None and not slugify(self.title):
            raise ValueError("Title does not produce a usable slug; send slug explicitly")
        return self

    @model_validator(mode="after")
    def salary_range(self) -> Self:
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max must be greater than or equal to salary_min")
        return self


class JobUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    company: str | None = Field(default=None, min_length=1, max_length=80)
    summary: str | None = Field(default=None, max_length=280)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    location: str | None = Field(default=None, max_length=80)
    work_mode: WorkMode | None = None
    employment_type: EmploymentType | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    skills: list[str] | None = Field(
        default=None,
        max_length=8,
        description="Replaces the whole skill list.",
    )

    @field_validator("skills")
    @classmethod
    def check_skills(cls, skills: list[str] | None) -> list[str] | None:
        if skills is None:
            return None
        return normalize_skills(skills)

    @model_validator(mode="after")
    def salary_range(self) -> Self:
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max must be greater than or equal to salary_min")
        return self


class JobRead(BaseModel):
    id: int
    title: str
    slug: str
    company: str
    summary: str
    description: str
    location: str
    work_mode: WorkMode
    employment_type: EmploymentType
    salary_min: int | None
    salary_max: int | None
    status: JobStatus
    skills: list[str]
    employer_id: int
    employer_name: str
    application_count: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class JobPage(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int


class SkillCount(BaseModel):
    name: str
    job_count: int
