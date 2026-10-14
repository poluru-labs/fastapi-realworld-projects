import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")


class MenuItemStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


class MenuItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    description: str = Field(default="", max_length=800)
    price_cents: int = Field(..., ge=0, le=1_000_000)
    category: str = Field(default="Mains", max_length=60)
    available: bool = Field(
        default=True,
        description="False when the kitchen cannot make this item right now.",
    )

    @model_validator(mode="after")
    def validate_slug(self) -> "MenuItemCreate":
        if self.slug is not None and not SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens")
        return self


class MenuItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=800)
    price_cents: int | None = Field(default=None, ge=0, le=1_000_000)
    category: str | None = Field(default=None, max_length=60)
    available: bool | None = None

    @model_validator(mode="after")
    def validate_partial(self) -> "MenuItemUpdate":
        return self


class MenuItemRead(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    price_cents: int
    category: str
    status: MenuItemStatus
    available: bool
    created_at: datetime
    updated_at: datetime
