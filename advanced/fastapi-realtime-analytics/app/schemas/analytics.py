import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STREAM_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class StreamStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class AlertStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class StreamCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(..., min_length=1, max_length=64, examples=["web-traffic"])
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)

    @field_validator("key")
    @classmethod
    def check_key(cls, key: str) -> str:
        key = key.casefold()
        if not STREAM_KEY_PATTERN.fullmatch(key):
            raise ValueError("Stream key must be lowercase words separated by hyphens")
        return key


class StreamUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class StreamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    description: str
    status: StreamStatus
    created_at: datetime
    updated_at: datetime


class EventIngest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_name: str = Field(..., min_length=1, max_length=64, examples=["page_view"])
    occurred_at: datetime | None = Field(
        default=None,
        description="Client timestamp. Defaults to server ingest time when omitted.",
    )
    properties: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str | None = Field(
        default=None,
        max_length=128,
        description="Optional stable id. Duplicate dedupe_key in the same stream returns 409.",
    )

    @field_validator("event_name")
    @classmethod
    def check_event_name(cls, name: str) -> str:
        if not _EVENT_NAME_PATTERN.fullmatch(name):
            raise ValueError("event_name must be snake_case starting with a letter")
        return name


class EventBatchIngest(BaseModel):
    events: list[EventIngest] = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def dedupe_keys_unique_in_batch(self) -> Self:
        seen: set[str] = set()
        for item in self.events:
            if item.dedupe_key is None:
                continue
            if item.dedupe_key in seen:
                raise ValueError("dedupe_key must be unique within a batch request")
            seen.add(item.dedupe_key)
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stream_id: int
    event_name: str
    occurred_at: datetime
    properties: dict[str, Any]
    dedupe_key: str | None
    ingested_at: datetime


class BatchIngestResult(BaseModel):
    accepted: int
    events: list[EventRead]


class MetricsOverview(BaseModel):
    stream_key: str
    total_events: int
    events_last_15m: int
    distinct_event_names_last_15m: int
    top_event_names_last_15m: list[tuple[str, int]] = Field(
        description="Up to five (event_name, count) pairs in the last 15 minutes."
    )


class TimeSeriesBucket(BaseModel):
    bucket_start: datetime
    count: int


class TimeSeriesRead(BaseModel):
    stream_key: str
    window_minutes: int
    bucket_seconds: int
    buckets: list[TimeSeriesBucket]


class AlertRuleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    window_minutes: int = Field(default=5, ge=1, le=1440)
    threshold_count: int = Field(..., ge=1, le=1_000_000)


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stream_id: int
    name: str
    window_minutes: int
    threshold_count: int
    status: AlertStatus
    created_at: datetime


class AlertEvaluation(BaseModel):
    rule: AlertRuleRead
    observed_count: int
    firing: bool
