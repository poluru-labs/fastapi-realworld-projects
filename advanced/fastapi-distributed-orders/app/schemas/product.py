from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    price_cents: int
    stock_quantity: int
    created_at: datetime


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    price_cents: int = Field(ge=0)
    stock_quantity: int = Field(ge=0, default=0)
