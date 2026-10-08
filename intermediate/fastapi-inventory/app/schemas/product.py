import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

SKU_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")


def normalize_sku(value: str) -> str:
    sku = value.strip().upper()
    if not SKU_PATTERN.fullmatch(sku):
        raise ValueError("SKU must be uppercase letters, digits, and hyphens only")
    return sku


class MovementType(StrEnum):
    RECEIVE = "receive"
    SALE = "sale"
    ADJUST = "adjust"


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(..., min_length=1, max_length=32, examples=["WIDGET-A"])
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    quantity_on_hand: int = Field(default=0, ge=0, description="Starting stock level.")
    reorder_level: int = Field(
        default=0,
        ge=0,
        description="At or below this level, the product counts as low stock.",
    )

    @field_validator("sku")
    @classmethod
    def check_sku(cls, sku: str) -> str:
        return normalize_sku(sku)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    reorder_level: int | None = Field(default=None, ge=0)

    @field_validator("description")
    @classmethod
    def empty_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    description: str
    quantity_on_hand: int
    reorder_level: int
    is_active: bool
    is_low_stock: bool = Field(
        description="True when quantity_on_hand is at or below reorder_level."
    )
    updated_at: datetime


class ReceiveStock(BaseModel):
    quantity: int = Field(..., ge=1, le=100_000, examples=[24])
    note: str = Field(default="", max_length=280, description="Optional shipment or PO reference.")


class SaleStock(BaseModel):
    quantity: int = Field(..., ge=1, le=100_000, examples=[2])
    note: str = Field(
        default="",
        max_length=280,
        description="Optional order or customer reference.",
    )


class AdjustStock(BaseModel):
    delta: int = Field(
        ...,
        ge=-100_000,
        le=100_000,
        examples=[-3],
        description="Signed change. Negative lowers stock. Result cannot go below zero.",
    )
    note: str = Field(default="", max_length=280, description="Why the count changed.")


class MovementRead(BaseModel):
    id: int
    product_id: int
    sku: str
    movement_type: MovementType
    delta: int = Field(description="Signed units added or removed.")
    quantity_after: int
    note: str
    actor_id: int
    actor_name: str
    created_at: datetime


class MovementPage(BaseModel):
    items: list[MovementRead]
    total: int
    limit: int
    offset: int
