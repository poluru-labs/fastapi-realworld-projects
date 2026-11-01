from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyScope(StrEnum):
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    METRICS_READ = "metrics:read"


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    scopes: list[ApiKeyScope] = Field(min_length=1, max_length=5)


class ApiKeyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    scopes: list[ApiKeyScope] | None = Field(default=None, min_length=1, max_length=5)


class ApiKeyRead(BaseModel):
    id: int
    name: str
    prefix: str
    scopes: list[ApiKeyScope]
    owner_id: int
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyCreated(BaseModel):
    key: ApiKeyRead
    secret: str = Field(description="Full API key — shown once. Store it securely.")
