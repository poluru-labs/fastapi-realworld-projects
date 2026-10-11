from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HoldStatus(StrEnum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    RELEASED = "released"
    EXPIRED = "expired"


class HoldCreate(BaseModel):
    tier_id: int = Field(ge=1)
    quantity: int = Field(ge=1, le=20)


class HoldRead(BaseModel):
    id: int
    tier_id: int
    tier_name: str
    event_slug: str
    event_title: str
    quantity: int
    status: HoldStatus
    expires_at: datetime
    created_at: datetime
