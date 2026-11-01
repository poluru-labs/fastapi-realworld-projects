import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


class FlagEnvironment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class FlagCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    environment: FlagEnvironment = FlagEnvironment.PRODUCTION
    enabled: bool = True
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    allowlist_user_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("key")
    @classmethod
    def check_key(cls, key: str) -> str:
        key = key.strip().casefold()
        if not KEY_PATTERN.fullmatch(key):
            raise ValueError("Key must start with a letter and use lowercase, digits, _ or -")
        return key

    @field_validator("allowlist_user_ids")
    @classmethod
    def normalize_allowlist(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            user_id = raw.strip()
            if user_id and user_id not in seen:
                seen.add(user_id)
                cleaned.append(user_id)
        return cleaned


class FlagUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    environment: FlagEnvironment | None = None
    enabled: bool | None = None
    rollout_percentage: int | None = Field(default=None, ge=0, le=100)
    allowlist_user_ids: list[str] | None = Field(default=None, max_length=50)

    @field_validator("allowlist_user_ids")
    @classmethod
    def normalize_allowlist(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return FlagCreate.normalize_allowlist(values)


class FlagRead(BaseModel):
    id: int
    key: str
    name: str
    description: str
    environment: FlagEnvironment
    enabled: bool
    rollout_percentage: int
    allowlist_user_ids: list[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime
