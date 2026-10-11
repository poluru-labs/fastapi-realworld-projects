import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProductStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


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


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(
        default=None,
        max_length=80,
        description="Optional URL slug. Generated from name when omitted.",
    )
    summary: str = Field(default="", max_length=280)
    description: str = Field(default="", max_length=8000)
    price_cents: int = Field(..., ge=0, le=10_000_000)
    stock: int = Field(default=0, ge=0, le=1_000_000)
    tags: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_slug_and_tags(self) -> "ProductCreate":
        if self.slug is not None and not SLUG_PATTERN.fullmatch(self.slug):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens")
        self.tags = normalize_tags(self.tags)
        return self


class ProductUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=280)
    description: str | None = Field(default=None, max_length=8000)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    tags: list[str] | None = Field(default=None, max_length=12)

    @model_validator(mode="after")
    def validate_tags(self) -> "ProductUpdate":
        if self.tags is not None:
            self.tags = normalize_tags(self.tags)
        return self


class ProductRead(BaseModel):
    id: int
    slug: str
    name: str
    summary: str
    description: str
    price_cents: int
    stock: int
    status: ProductStatus
    vendor_id: int
    vendor_name: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None


class TagCount(BaseModel):
    name: str
    count: int
