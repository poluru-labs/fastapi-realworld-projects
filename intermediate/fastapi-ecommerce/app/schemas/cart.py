from pydantic import BaseModel, ConfigDict, Field


class CartLineRead(BaseModel):
    product_id: int
    product_slug: str
    product_name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class CartRead(BaseModel):
    items: list[CartLineRead]
    item_count: int
    subtotal_cents: int


class CartLineUpsert(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_slug: str = Field(..., min_length=1, max_length=80)
    quantity: int = Field(..., ge=1, le=99)
