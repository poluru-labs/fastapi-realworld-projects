from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WalletEventType(StrEnum):
    WALLET_CREATED = "wallet_created"
    MONEY_DEPOSITED = "money_deposited"
    MONEY_WITHDRAWN = "money_withdrawn"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"


class WalletCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, value: str) -> str:
        return value.upper()


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: int
    name: str
    currency: str
    balance_cents: int
    version: int
    created_at: datetime


class MoneyCommand(BaseModel):
    amount_cents: int = Field(..., ge=1, le=100_000_000)
    expected_version: int = Field(
        ...,
        ge=0,
        description="Optimistic concurrency: must match the wallet `version` you last read.",
    )
    memo: str = Field(default="", max_length=200)


class TransferCreate(BaseModel):
    from_wallet_id: str = Field(..., min_length=36, max_length=36)
    to_wallet_id: str = Field(..., min_length=36, max_length=36)
    amount_cents: int = Field(..., ge=1, le=100_000_000)
    expected_version: int = Field(..., ge=0, description="Version of the source wallet.")
    memo: str = Field(default="", max_length=200)


class TransferResult(BaseModel):
    from_wallet: WalletRead
    to_wallet: WalletRead


class WalletEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    event_type: str
    payload: dict
    created_at: datetime
