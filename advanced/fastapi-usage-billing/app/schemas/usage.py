from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UsageEventCreate(BaseModel):
    meter_code: str = Field(..., examples=["api_calls"])
    quantity: Decimal = Field(..., gt=0, examples=["1"])
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique per customer. Replays return the original event (no double-count).",
        examples=["evt_2026_04_01_001"],
    )
    recorded_at: datetime | None = Field(
        None,
        description="When usage happened in your product. Defaults to server time.",
    )


class UsageEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    meter_code: str
    quantity: Decimal
    idempotency_key: str
    recorded_at: datetime
    request_id: str | None


class UsageMeterTotal(BaseModel):
    meter_code: str
    quantity: Decimal


class UsageSummaryRead(BaseModel):
    customer_id: int
    period_start: datetime
    period_end: datetime
    totals: list[UsageMeterTotal]
