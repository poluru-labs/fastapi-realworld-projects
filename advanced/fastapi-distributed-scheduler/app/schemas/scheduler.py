import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ScheduleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ScheduleKind(StrEnum):
    CRON = "cron"
    INTERVAL = "interval"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:64].strip("-")


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    schedule_kind: ScheduleKind
    cron_expression: str | None = Field(default=None, max_length=120)
    interval_seconds: int | None = Field(default=None, ge=60, le=86_400)
    timezone: str = Field(default="UTC", max_length=64)
    task_type: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    default_payload: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)
    slug: str | None = Field(default=None, max_length=64)

    @field_validator("slug")
    @classmethod
    def check_slug(cls, slug: str | None) -> str | None:
        if slug is None:
            return None
        slug = slug.strip().casefold()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return slug

    @model_validator(mode="after")
    def schedule_fields(self) -> Self:
        if self.schedule_kind is ScheduleKind.CRON and not self.cron_expression:
            raise ValueError("cron_expression is required when schedule_kind is cron")
        if self.schedule_kind is ScheduleKind.INTERVAL and self.interval_seconds is None:
            raise ValueError("interval_seconds is required when schedule_kind is interval")
        if self.slug is None and not slugify(self.name):
            raise ValueError("Title does not produce a usable slug; send slug explicitly")
        return self


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    cron_expression: str | None = Field(default=None, max_length=120)
    interval_seconds: int | None = Field(default=None, ge=60, le=86_400)
    timezone: str | None = Field(default=None, max_length=64)
    default_payload: dict[str, Any] | None = None
    max_attempts: int | None = Field(default=None, ge=1, le=10)
    retry_delay_seconds: int | None = Field(default=None, ge=1, le=3600)


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    status: ScheduleStatus
    schedule_kind: ScheduleKind
    cron_expression: str | None
    interval_seconds: int | None
    timezone: str
    task_type: str
    default_payload: dict[str, Any]
    max_attempts: int
    retry_delay_seconds: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class TriggerRunRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    scheduled_for: datetime | None = Field(
        default=None,
        description="Defaults to now. Must not be in the past by more than a few seconds.",
    )


class ScheduledRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int | None
    owner_id: int
    task_type: str
    payload: dict[str, Any]
    status: RunStatus
    scheduled_for: datetime
    attempt_count: int
    max_attempts: int
    retry_delay_seconds: int
    lease_holder: str | None
    lease_expires_at: datetime | None
    version: int
    result: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class WorkerRegister(BaseModel):
    worker_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    capabilities: list[str] = Field(..., min_length=1, max_length=16)

    @field_validator("capabilities")
    @classmethod
    def normalize_caps(cls, caps: list[str]) -> list[str]:
        return sorted({c.strip().casefold() for c in caps if c.strip()})


class WorkerHeartbeat(BaseModel):
    worker_id: str = Field(..., min_length=1, max_length=64)


class ClaimRunRequest(BaseModel):
    worker_id: str = Field(..., min_length=1, max_length=64)


class CompleteRunRequest(BaseModel):
    worker_id: str = Field(..., min_length=1, max_length=64)
    expected_version: int = Field(..., ge=1)
    outcome: RunOutcome
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = Field(default=None, max_length=2000)
