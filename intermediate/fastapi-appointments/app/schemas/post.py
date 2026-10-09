import re
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PostStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def slugify(value: str) -> str:
    """Turn a title into a URL slug. Empty when the title has no letters or digits."""
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


class PostCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=120,
        examples=["Pagination without leaking drafts"],
    )
    summary: str = Field(
        default="",
        max_length=280,
        description="Short blurb for the public list. Omit it and the list still works.",
    )
    body: str = Field(..., min_length=1, max_length=20_000)
    tags: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Up to 8 tags. Case is ignored and duplicates are dropped.",
        examples=[["fastapi", "pagination"]],
    )
    slug: str | None = Field(
        default=None,
        max_length=80,
        description=(
            "Public URL id. Omit it and the slug is derived from the title. "
            "A slug never changes after create."
        ),
        examples=["pagination-without-leaking-drafts"],
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

    @field_validator("tags")
    @classmethod
    def check_tags(cls, tags: list[str]) -> list[str]:
        return normalize_tags(tags)

    @model_validator(mode="after")
    def title_can_slugify(self) -> Self:
        if self.slug is None and not slugify(self.title):
            raise ValueError("Title does not produce a usable slug; send slug explicitly")
        return self


class PostUpdate(BaseModel):
    """Partial edit. Omitted fields stay as they are. The slug is not editable."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=280)
    body: str | None = Field(default=None, min_length=1, max_length=20_000)
    tags: list[str] | None = Field(
        default=None,
        max_length=8,
        description="Replaces the whole tag list. Send an empty list to clear tags.",
    )

    @field_validator("tags")
    @classmethod
    def check_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        return normalize_tags(tags)


class PostRead(BaseModel):
    id: int
    title: str
    slug: str = Field(description="Stable public id. Use this in URLs, not the numeric id.")
    summary: str
    body: str
    status: PostStatus
    tags: list[str]
    author_id: int
    author_name: str
    comment_count: int = Field(description="Comments stored on this post right now.")
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = Field(
        description="When it last moved to published. Null for a draft that has never been live."
    )


class PostPage(BaseModel):
    items: list[PostRead]
    total: int = Field(description="Matches before limit and offset are applied.")
    limit: int
    offset: int


class TagCount(BaseModel):
    name: str = Field(description="Lowercase tag, exactly as stored on posts.")
    post_count: int = Field(
        description="Published posts that include this tag. Drafts are excluded."
    )
