import re
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TicketStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


def normalize_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        tag = raw.strip().casefold()
        if not _TAG_PATTERN.fullmatch(tag) or len(tag) > 32:
            raise ValueError(
                "Tags must be lowercase words, optionally hyphenated, up to 32 characters"
            )
        if tag not in seen:
            seen.add(tag)
            cleaned.append(tag)
    return cleaned


class TicketCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    summary: str = Field(default="", max_length=280)
    description: str = Field(..., min_length=1, max_length=20_000)
    priority: TicketPriority = TicketPriority.NORMAL
    tags: list[str] = Field(default_factory=list, max_length=8)
    slug: str | None = Field(default=None, max_length=80)

    @field_validator("slug")
    @classmethod
    def check_slug(cls, slug: str | None) -> str | None:
        if slug is None:
            return None
        slug = slug.strip().casefold()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return slug

    @field_validator("tags")
    @classmethod
    def check_tags(cls, tags: list[str]) -> list[str]:
        return normalize_tags(tags)

    @model_validator(mode="after")
    def title_can_slugify(self) -> Self:
        if self.slug is None and not slugify(self.title):
            raise ValueError("Title does not produce a usable slug; send slug explicitly")
        return self


class TicketUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=280)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    priority: TicketPriority | None = None
    tags: list[str] | None = Field(default=None, max_length=8)
    assignee_id: int | None = Field(default=None, ge=1)

    @field_validator("tags")
    @classmethod
    def check_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        return normalize_tags(tags)


class TicketRead(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    tags: list[str]
    requester_id: int
    requester_name: str
    assignee_id: int | None
    assignee_name: str | None
    reply_count: int
    created_at: datetime
    updated_at: datetime
    opened_at: datetime | None


class TicketPage(BaseModel):
    items: list[TicketRead]
    total: int
    limit: int
    offset: int


class CategoryCount(BaseModel):
    name: str
    ticket_count: int
