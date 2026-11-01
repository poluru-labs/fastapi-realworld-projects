import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")


class CheckStatus(StrEnum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


class MonitorCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    target_url: HttpUrl
    slug: str | None = Field(default=None, max_length=80)
    expected_status: int = Field(default=200, ge=100, le=599)
    is_public: bool = False

    @field_validator("slug")
    @classmethod
    def check_slug(cls, slug: str | None) -> str | None:
        if slug is None:
            return None
        slug = slug.strip().casefold()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return slug


class MonitorUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    target_url: HttpUrl | None = None
    expected_status: int | None = Field(default=None, ge=100, le=599)
    is_public: bool | None = None


class CheckResultRead(BaseModel):
    id: int
    monitor_slug: str
    status: CheckStatus
    http_status: int | None
    latency_ms: int
    message: str
    checked_at: datetime


class MonitorRead(BaseModel):
    id: int
    slug: str
    name: str
    target_url: str
    expected_status: int
    is_active: bool
    is_public: bool
    owner_id: int
    last_status: CheckStatus | None
    last_checked_at: datetime | None
    status_page_path: str | None
    created_at: datetime


class StatusPageRead(BaseModel):
    slug: str
    name: str
    status: CheckStatus
    target_url: str
    last_checked_at: datetime | None
    latency_ms: int | None
    recent_checks: list[CheckResultRead]
