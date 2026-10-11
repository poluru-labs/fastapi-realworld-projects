import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


class TierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price_cents: int = Field(ge=0)
    capacity: int = Field(ge=1, le=100_000)


class TierRead(BaseModel):
    id: int
    name: str
    price_cents: int
    capacity: int
    quantity_sold: int
    quantity_held: int
    quantity_available: int


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    slug: str | None = Field(default=None, max_length=80)
    description: str = Field(default="", max_length=4000)
    venue_id: int = Field(ge=1)
    starts_at: datetime


class EventRead(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    venue_id: int
    venue_name: str
    city: str
    starts_at: datetime
    status: EventStatus
    tiers: list[TierRead]
    created_at: datetime
