import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class BillingInterval(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


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


class PlanCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    summary: str = Field(default="", max_length=280)
    description: str = Field(default="", max_length=8000)
    price_cents: int = Field(..., ge=0, le=10_000_000)
    interval: BillingInterval = Field(default=BillingInterval.MONTHLY)
    tags: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_slug_and_tags(self) -> "PlanCreate":
        if self.slug is not None and not SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens")
        self.tags = normalize_tags(self.tags)
        return self


class PlanUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=280)
    description: str | None = Field(default=None, max_length=8000)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    interval: BillingInterval | None = None
    tags: list[str] | None = Field(default=None, max_length=12)

    @model_validator(mode="after")
    def validate_tags(self) -> "PlanUpdate":
        if self.tags is not None:
            self.tags = normalize_tags(self.tags)
        return self


class PlanRead(BaseModel):
    id: int
    slug: str
    name: str
    summary: str
    description: str
    price_cents: int
    interval: BillingInterval
    status: PlanStatus
    owner_id: int
    owner_name: str
    tags: list[str]
    active_subscriber_count: int
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None


class TagCount(BaseModel):
    name: str
    count: int
