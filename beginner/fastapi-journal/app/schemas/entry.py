from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class Mood(StrEnum):
    GREAT = "great"
    GOOD = "good"
    OKAY = "okay"
    LOW = "low"
    ROUGH = "rough"


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


class EntryCreate(BaseModel):
    entry_date: date = Field(..., description="Calendar day for this journal entry.")
    title: str = Field(default="", max_length=120)
    body: str = Field(..., min_length=1, max_length=10_000)
    mood: Mood | None = None
    tags: list[str] = Field(default_factory=list, max_length=12)
    starred: bool = False

    @field_validator("title", "body", mode="before")
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


class EntryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, min_length=1, max_length=10_000)
    mood: Mood | None = None
    tags: list[str] | None = Field(default=None, max_length=12)
    starred: bool | None = None

    @field_validator("title", "body", mode="before")
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


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_date: date
    title: str
    body: str
    mood: Mood | None
    tags: list[str]
    starred: bool
    created_at: datetime
    updated_at: datetime


class EntryDeleteResponse(BaseModel):
    deleted: bool = True
    id: int


class TagListResponse(BaseModel):
    tags: list[str]
