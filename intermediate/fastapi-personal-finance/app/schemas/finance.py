import re
from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_REPLACE = re.compile(r"[^a-z0-9]+")
_CATEGORY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"


class TransactionStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


def slugify(value: str) -> str:
    return _SLUG_REPLACE.sub("-", value.casefold()).strip("-")[:80].strip("-")


def normalize_category(value: str) -> str:
    category = value.strip().casefold()
    if not _CATEGORY_PATTERN.fullmatch(category) or len(category) > 32:
        raise ValueError(
            "Category must be lowercase words, optionally hyphenated, up to 32 characters"
        )
    return category


class AccountCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    account_type: AccountType = AccountType.CHECKING
    currency: str = Field(default="USD", min_length=3, max_length=3)
    opening_balance: float = Field(
        default=0.0,
        description="Starting balance before posted activity.",
    )
    slug: str | None = Field(default=None, max_length=80)

    @field_validator("slug")
    @classmethod
    def check_slug(cls, slug: str | None) -> str | None:
        if slug is None:
            return None
        slug = slug.strip().casefold()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return slug

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, currency: str) -> str:
        return currency.upper()

    @model_validator(mode="after")
    def name_can_slugify(self) -> Self:
        if self.slug is None and not slugify(self.name):
            raise ValueError("Name does not produce a usable slug; send slug explicitly")
        return self


class AccountUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    slug: str
    name: str
    account_type: AccountType
    currency: str
    opening_balance: float
    current_balance: float
    archived: bool
    created_at: datetime
    updated_at: datetime


class AccountPage(BaseModel):
    items: list[AccountRead]
    total: int
    limit: int
    offset: int


class TransactionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: float = Field(
        ...,
        description="Signed amount: negative for expenses, positive for income.",
    )
    category: str = Field(..., min_length=1, max_length=32)
    payee: str = Field(default="", max_length=120)
    memo: str = Field(default="", max_length=500)
    occurred_on: date

    @field_validator("category")
    @classmethod
    def check_category(cls, category: str) -> str:
        return normalize_category(category)


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: float | None = None
    category: str | None = Field(default=None, min_length=1, max_length=32)
    payee: str | None = Field(default=None, max_length=120)
    memo: str | None = Field(default=None, max_length=500)
    occurred_on: date | None = None

    @field_validator("category")
    @classmethod
    def check_category(cls, category: str | None) -> str | None:
        if category is None:
            return None
        return normalize_category(category)


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    owner_id: int
    amount: float
    category: str
    payee: str
    memo: str
    occurred_on: date
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionRead]
    total: int
    limit: int
    offset: int


class CategorySpend(BaseModel):
    category: str
    total_spent: float = Field(description="Sum of absolute expense amounts (posted, negative).")
