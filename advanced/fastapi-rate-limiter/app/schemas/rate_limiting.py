import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


class PolicyStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class PolicyCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "key": "partner-api",
                    "name": "Partner API",
                    "description": "Fixed window for B2B integrations.",
                    "limit": 100,
                    "window_seconds": 60,
                }
            ]
        },
    )

    key: str = Field(..., min_length=2, max_length=64, pattern=KEY_PATTERN.pattern)
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    limit: int = Field(..., ge=1, le=1_000_000)
    window_seconds: int = Field(..., ge=1, le=86_400)


class PolicyRead(BaseModel):
    id: int
    key: str
    name: str
    description: str
    limit: int
    window_seconds: int
    status: PolicyStatus


class ClientCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "key": "mobile-app",
                    "name": "Mobile app backend",
                    "policy_key": "public-api",
                }
            ]
        },
    )

    key: str = Field(..., min_length=2, max_length=64, pattern=KEY_PATTERN.pattern)
    name: str = Field(..., min_length=1, max_length=120)
    policy_key: str = Field(..., min_length=2, max_length=64)


class ClientRead(BaseModel):
    id: int
    key: str
    name: str
    policy_key: str
    policy_limit: int
    window_seconds: int


class ClientProvisioned(ClientRead):
    client_key: str = Field(description="Shown once — store securely for X-Client-Key header")


class QuotaRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"subject_key": "device-abc", "cost": 1},
            ]
        },
    )

    subject_key: str = Field(..., min_length=1, max_length=128)
    cost: int = Field(default=1, ge=1, le=1000)


class QuotaStatus(BaseModel):
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    policy_key: str
    client_key: str
    subject_key: str
    window_count: int


class SubjectUsageRow(BaseModel):
    subject_key: str
    window_count: int
    remaining: int
