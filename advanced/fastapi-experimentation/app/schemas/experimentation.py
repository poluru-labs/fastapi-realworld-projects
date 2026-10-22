import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXPERIMENT_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    STOPPED = "stopped"


class EventType(StrEnum):
    EXPOSURE = "exposure"
    CONVERSION = "conversion"


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(..., min_length=2, max_length=64, examples=["checkout-button"])
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)

    @field_validator("key")
    @classmethod
    def normalize_key(cls, key: str) -> str:
        key = key.casefold()
        if not EXPERIMENT_KEY_PATTERN.fullmatch(key):
            raise ValueError("Experiment key must be lowercase words separated by hyphens")
        return key


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    description: str
    status: ExperimentStatus
    started_at: datetime | None
    stopped_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExperimentProvisioned(ExperimentRead):
    ingest_token: str = Field(description="Shown once at provision time.")


class VariantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(..., min_length=1, max_length=32, examples=["control"])
    name: str = Field(..., min_length=1, max_length=120)
    weight: int = Field(..., ge=0, le=100)


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    key: str
    name: str
    weight: int


class ExperimentDetail(ExperimentRead):
    variants: list[VariantRead]


class AssignmentRead(BaseModel):
    experiment_key: str
    subject_id: str
    variant_key: str
    variant_name: str


class EventIngest(BaseModel):
    subject_id: str = Field(..., min_length=1, max_length=128)
    event_type: EventType
    variant_key: str = Field(..., min_length=1, max_length=32)
    occurred_at: datetime | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str | None = Field(default=None, max_length=128)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    subject_id: str
    event_type: EventType
    variant_key: str
    occurred_at: datetime
    properties: dict[str, Any]
    ingested_at: datetime


class VariantResults(BaseModel):
    variant_key: str
    exposures: int
    conversions: int
    conversion_rate: float | None


class ExperimentResults(BaseModel):
    experiment_key: str
    window_minutes: int
    variants: list[VariantResults]
