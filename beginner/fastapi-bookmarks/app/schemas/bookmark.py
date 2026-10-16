from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tags:
        t = raw.strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= 12:
            break
    return out


class BookmarkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, description="Short label in your list.")
    url: HttpUrl = Field(..., description="Must be http or https.")
    tags: list[str] = Field(default_factory=list, max_length=12)
    note: str = Field(default="", max_length=500)
    pinned: bool = False

    @field_validator("title", "note", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        return _normalize_tags([str(v) for v in value])


class BookmarkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    url: HttpUrl | None = None
    tags: list[str] | None = Field(default=None, max_length=12)
    note: str | None = Field(default=None, max_length=500)
    pinned: bool | None = None

    @field_validator("title", "note", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list):
            return []
        return _normalize_tags([str(v) for v in value])


class BookmarkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    tags: list[str]
    note: str
    pinned: bool
    archived: bool
    created_at: datetime
    updated_at: datetime


class BookmarkDeleteResponse(BaseModel):
    deleted: bool = True
    id: int


class TagListResponse(BaseModel):
    tags: list[str]
