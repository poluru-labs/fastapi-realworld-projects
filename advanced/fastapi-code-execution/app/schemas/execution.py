from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RunLanguage(StrEnum):
    PYTHON = "python"


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


class RunCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    language: RunLanguage = RunLanguage.PYTHON
    source: str = Field(min_length=1, max_length=20_000)


class RunRead(BaseModel):
    id: int
    language: RunLanguage
    source: str
    status: RunStatus
    stdout: str
    stderr: str
    exit_code: int | None
    runtime_ms: int
    idempotency_key: str | None
    created_at: datetime
    finished_at: datetime | None


class PolicyRead(BaseModel):
    max_source_bytes: int
    max_timeout_ms: int
    allowed_languages: list[RunLanguage]
    updated_at: datetime


class PolicyUpdate(BaseModel):
    max_source_bytes: int | None = Field(default=None, ge=256, le=50_000)
    max_timeout_ms: int | None = Field(default=None, ge=100, le=30_000)
    allowed_languages: list[RunLanguage] | None = Field(default=None, min_length=1, max_length=5)
