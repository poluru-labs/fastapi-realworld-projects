from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AggregateStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class FragmentStep(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")
    source_slug: str = Field(min_length=3, max_length=40)
    path: str = Field(min_length=1, max_length=200)
    method: Literal["GET"] = "GET"


class AggregateCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slug: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    steps: list[FragmentStep] = Field(min_length=1, max_length=10)


class AggregateUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    steps: list[FragmentStep] | None = Field(default=None, min_length=1, max_length=10)


class AggregateRead(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    status: AggregateStatus
    steps: list[FragmentStep]
    owner_id: int
    run_path: str
    created_at: datetime


class FragmentResult(BaseModel):
    key: str
    source_slug: str
    status_code: int
    data: dict | None = None
    error: str | None = None


class AggregateRunRead(BaseModel):
    id: int
    aggregate_slug: str
    partial: bool
    fragments: list[FragmentResult]
    idempotency_key: str | None
    created_at: datetime
