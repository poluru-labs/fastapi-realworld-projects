import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


def normalize_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        tag = raw.strip().casefold()
        if not _TAG_PATTERN.fullmatch(tag) or len(tag) > 32:
            msg = "Tags must be lowercase words, optionally hyphenated, up to 32 characters"
            raise ValueError(msg)
        if tag not in seen:
            seen.add(tag)
            cleaned.append(tag)
    return cleaned


class EventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(
        default=None,
        max_length=80,
        description="Optional URL slug. Generated from title when omitted.",
    )
    summary: str = Field(default="", max_length=280)
    description: str = Field(default="", max_length=8000)
    location: str = Field(default="", max_length=200)
    starts_at: datetime = Field(..., description="ISO-8601 datetime with timezone offset.")
    ends_at: datetime = Field(..., description="Must be after starts_at.")
    capacity: int = Field(default=50, ge=1, le=10_000)
    tags: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_window(self) -> "EventCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.slug is not None and not SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens")
        self.tags = normalize_tags(self.tags)
        return self


class EventUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=280)
    description: str | None = Field(default=None, max_length=8000)
    location: str | None = Field(default=None, max_length=200)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=10_000)
    tags: list[str] | None = Field(default=None, max_length=12)

    @model_validator(mode="after")
    def validate_partial(self) -> "EventUpdate":
        if self.starts_at is not None and self.ends_at is not None:
            if self.ends_at <= self.starts_at:
                raise ValueError("ends_at must be after starts_at")
        if self.tags is not None:
            self.tags = normalize_tags(self.tags)
        return self


class EventRead(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: EventStatus
    organizer_id: int
    organizer_name: str
    tags: list[str]
    registered_count: int
    waitlist_count: int
    seats_available: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class TagCount(BaseModel):
    name: str
    count: int
