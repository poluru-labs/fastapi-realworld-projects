from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    external_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Your id for this account (unique across the billing API).",
        examples=["acct_9f3c"],
    )
    name: str = Field(..., min_length=1, max_length=200, examples=["Acme Corp"])


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    name: str
    created_at: datetime


class CustomerCreated(CustomerRead):
    """Returned once on create. Store `api_key` securely — it is not shown again."""

    api_key: str = Field(..., description="Customer credential for usage ingestion and /me routes")
