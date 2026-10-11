from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(StrEnum):
    PLACED = "placed"
    CANCELLED = "cancelled"


class OrderLineRead(BaseModel):
    product_id: int
    product_slug: str
    product_name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderRead(BaseModel):
    id: int
    user_id: int
    buyer_name: str
    status: OrderStatus
    total_cents: int
    items: list[OrderLineRead]
    created_at: datetime


class CheckoutCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    note: str = Field(default="", max_length=280)
