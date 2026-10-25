from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"


class SubscriptionCreate(BaseModel):
    plan_code: str = Field(..., examples=["starter"])


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    plan_code: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
