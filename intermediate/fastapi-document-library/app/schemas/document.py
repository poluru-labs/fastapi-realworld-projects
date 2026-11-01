import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.folder import SLUG_PATTERN

_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


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


class DocumentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(default="", max_length=280)
    body: str = Field(min_length=1, max_length=20_000)
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


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=280)
    body: str | None = Field(default=None, min_length=1, max_length=20_000)
    tags: list[str] | None = Field(default=None, max_length=8)

    @field_validator("tags")
    @classmethod
    def check_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        return normalize_tags(tags)


class DocumentRead(BaseModel):
    id: int
    folder_slug: str
    slug: str
    title: str
    summary: str
    body: str
    status: DocumentStatus
    tags: list[str]
    author_id: int
    author_name: str
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class DocumentPage(BaseModel):
    items: list[DocumentRead]
    total: int
    limit: int
    offset: int


class RevisionRead(BaseModel):
    version: int
    title: str
    body: str
    published_at: datetime


class TagCount(BaseModel):
    name: str
    document_count: int
