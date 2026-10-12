from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    plan_slug: str = Field(..., min_length=1, max_length=80)


class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    subscriber_name: str
    plan_id: int
    plan_slug: str
    plan_name: str
    price_cents: int
    interval: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
    cancelled_at: datetime | None
