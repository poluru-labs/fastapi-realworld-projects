import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


class EndpointStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    ACKED = "acked"


class EndpointCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "slug": "billing-stripe",
                    "name": "Stripe billing",
                    "description": "Checkout and subscription events.",
                }
            ]
        },
    )

    slug: str = Field(..., min_length=2, max_length=64, pattern=SLUG_PATTERN.pattern)
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class EndpointUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: EndpointStatus | None = None


class EndpointRead(BaseModel):
    id: int
    owner_id: int
    slug: str
    name: str
    description: str
    status: EndpointStatus
    delivery_count: int
    pending_count: int
    ingest_path: str
    created_at: datetime


class EndpointProvisioned(EndpointRead):
    webhook_token: str = Field(
        description="Shown once — send as X-Webhook-Token on ingest requests."
    )


class DeliveryIngest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_type": "invoice.paid",
                    "payload": {"id": "inv_123", "amount": 9900, "currency": "usd"},
                }
            ]
        },
    )

    event_type: str = Field(..., min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class DeliveryRead(BaseModel):
    id: int
    endpoint_id: int
    endpoint_slug: str
    event_type: str
    payload: dict[str, Any]
    status: DeliveryStatus
    retry_count: int
    received_at: datetime
    acked_at: datetime | None
