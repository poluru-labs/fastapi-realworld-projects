from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class PaymentMethod(StrEnum):
    CARD = "card"
    CASH = "cash"
    TRANSFER = "transfer"


class ExpenseCreate(BaseModel):
    merchant: str = Field(..., min_length=1, max_length=120, description="Payee or store name.")
    amount_cents: int = Field(..., ge=1, le=100_000_000, description="Amount in cents.")
    category: str = Field(default="General", max_length=60)
    spent_on: date = Field(..., description="Calendar date of the purchase (YYYY-MM-DD).")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CARD)
    note: str = Field(default="", max_length=500)
    receipt_ref: str | None = Field(
        default=None,
        max_length=64,
        description="Optional receipt id. Must be unique when set.",
    )
    flagged: bool = Field(
        default=False,
        description="Flagged expenses sort first for review.",
    )

    @field_validator("merchant", "category", "note", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("receipt_ref", mode="before")
    @classmethod
    def strip_receipt(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class ExpenseUpdate(BaseModel):
    merchant: str | None = Field(default=None, min_length=1, max_length=120)
    amount_cents: int | None = Field(default=None, ge=1, le=100_000_000)
    category: str | None = Field(default=None, max_length=60)
    spent_on: date | None = None
    payment_method: PaymentMethod | None = None
    note: str | None = Field(default=None, max_length=500)
    receipt_ref: str | None = Field(default=None, max_length=64)
    flagged: bool | None = None

    @field_validator("merchant", "category", "note", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("receipt_ref", mode="before")
    @classmethod
    def strip_receipt(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant: str
    amount_cents: int
    category: str
    spent_on: date
    payment_method: PaymentMethod
    note: str
    receipt_ref: str | None
    flagged: bool


class CategoryTotal(BaseModel):
    category: str
    total_cents: int
    count: int


class ExpenseSummary(BaseModel):
    total_cents: int
    count: int
    by_category: list[CategoryTotal]


class ExpenseDeleteResponse(BaseModel):
    deleted: bool = True
    expense: ExpenseRead
