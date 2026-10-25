from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InvoiceStatus(StrEnum):
    OPEN = "open"
    PAID = "paid"


class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meter_code: str
    quantity: Decimal
    included_quantity: Decimal
    billable_quantity: Decimal
    unit_price_cents: int
    amount_cents: int


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    period_start: datetime
    period_end: datetime
    total_cents: int
    status: InvoiceStatus
    created_at: datetime
    lines: list[InvoiceLineRead]


class InvoicePreviewRead(BaseModel):
    """Computed charges for the active subscription period. Nothing is persisted."""

    customer_id: int
    period_start: datetime
    period_end: datetime
    total_cents: int = Field(..., description="Sum of line `amount_cents` values")
    lines: list[InvoiceLineRead]
