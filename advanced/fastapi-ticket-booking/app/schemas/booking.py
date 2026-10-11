from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class BookingCreate(BaseModel):
    hold_id: int = Field(ge=1, description="Active hold from POST /holds")


class BookingItemRead(BaseModel):
    tier_id: int
    tier_name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class BookingRead(BaseModel):
    id: int
    confirmation_code: str
    event_slug: str
    event_title: str
    status: BookingStatus
    total_cents: int
    items: list[BookingItemRead]
    created_at: datetime
