from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class OrderLineCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    items: list[OrderLineCreate] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_skus(self) -> "OrderCreate":
        skus = [line.sku for line in self.items]
        if len(skus) != len(set(skus)):
            raise ValueError("Duplicate sku in the same order")
        return self


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_sku: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderRead(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    version: int
    correlation_id: str
    total_cents: int
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime


class OrderTransition(BaseModel):
    expected_version: int = Field(
        ge=1,
        description="Optimistic lock. Must match the order's current version.",
    )
