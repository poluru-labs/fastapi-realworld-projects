import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEVICE_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_METRIC_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class DeviceStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DECOMMISSIONED = "decommissioned"


class AlertStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class Comparator(StrEnum):
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"


class DeviceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(..., min_length=2, max_length=64, examples=["warehouse-temp-01"])
    name: str = Field(..., min_length=1, max_length=120)
    site: str = Field(default="", max_length=120)

    @field_validator("key")
    @classmethod
    def normalize_key(cls, key: str) -> str:
        key = key.casefold()
        if not DEVICE_KEY_PATTERN.fullmatch(key):
            raise ValueError("Device key must be lowercase words separated by hyphens")
        return key


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    site: str
    status: DeviceStatus
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeviceProvisioned(DeviceRead):
    ingest_token: str = Field(
        description="Shown once at provision time. Store it on the device firmware."
    )


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    site: str | None = Field(default=None, max_length=120)


class ReadingIngest(BaseModel):
    recorded_at: datetime | None = Field(
        default=None,
        description="Edge timestamp. Server time is used when omitted.",
    )
    metrics: dict[str, float | int | bool | str] = Field(
        ...,
        min_length=1,
        examples=[{"temp_c": 22.4, "humidity_pct": 41}],
    )
    dedupe_key: str | None = Field(default=None, max_length=128)

    @field_validator("metrics")
    @classmethod
    def metric_keys(cls, metrics: dict[str, Any]) -> dict[str, Any]:
        for key in metrics:
            if not _METRIC_KEY_PATTERN.fullmatch(key):
                raise ValueError("Metric keys must be snake_case")
        return metrics


class ReadingBatchIngest(BaseModel):
    readings: list[ReadingIngest] = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_dedupe(self) -> Self:
        seen: set[str] = set()
        for row in self.readings:
            if row.dedupe_key is None:
                continue
            if row.dedupe_key in seen:
                raise ValueError("dedupe_key must be unique within a batch")
            seen.add(row.dedupe_key)
        return self


class ReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    recorded_at: datetime
    metrics: dict[str, Any]
    dedupe_key: str | None
    ingested_at: datetime


class BatchIngestResult(BaseModel):
    accepted: int
    readings: list[ReadingRead]


class DeviceOverview(BaseModel):
    device_key: str
    status: DeviceStatus
    total_readings: int
    readings_last_hour: int
    last_seen_at: datetime | None
    latest_metrics: dict[str, Any] | None


class MetricSeriesPoint(BaseModel):
    recorded_at: datetime
    value: float


class MetricSeriesRead(BaseModel):
    device_key: str
    metric_key: str
    window_minutes: int
    points: list[MetricSeriesPoint]


class AlertRuleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    metric_key: str = Field(..., min_length=1, max_length=64)
    window_minutes: int = Field(default=15, ge=1, le=1440)
    threshold: float
    comparator: Comparator = Comparator.GTE

    @field_validator("metric_key")
    @classmethod
    def check_metric(cls, key: str) -> str:
        if not _METRIC_KEY_PATTERN.fullmatch(key):
            raise ValueError("metric_key must be snake_case")
        return key


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    name: str
    metric_key: str
    window_minutes: int
    threshold: float
    comparator: Comparator
    status: AlertStatus
    created_at: datetime


class AlertEvaluation(BaseModel):
    rule: AlertRuleRead
    observed_value: float | None
    firing: bool
