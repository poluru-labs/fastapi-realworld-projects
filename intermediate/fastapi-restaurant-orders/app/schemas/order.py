from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(StrEnum):
    PLACED = "placed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderLineCreate(BaseModel):
    menu_item_slug: str = Field(..., min_length=1, max_length=80)
    quantity: int = Field(..., ge=1, le=20)


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    lines: list[OrderLineCreate] = Field(..., min_length=1, max_length=20)
    note: str = Field(default="", max_length=280)


class OrderLineRead(BaseModel):
    menu_item_id: int
    menu_item_slug: str
    menu_item_name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderRead(BaseModel):
    id: int
    user_id: int
    customer_name: str
    status: OrderStatus
    total_cents: int
    note: str
    items: list[OrderLineRead]
    created_at: datetime
    updated_at: datetime
