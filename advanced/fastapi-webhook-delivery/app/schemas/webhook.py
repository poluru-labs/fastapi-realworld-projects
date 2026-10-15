from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class DeliveryStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WebhookEndpointCreate(BaseModel):
    url: AnyHttpUrl = Field(description="HTTPS (or http://testserver in tests) subscriber URL.")
    description: str = Field(default="", max_length=500)
    event_types: list[str] = Field(
        default_factory=lambda: ["*"],
        description='Subscribe to these types, or ["*"] for all events you publish.',
    )
    enabled: bool = True

    @field_validator("event_types")
    @classmethod
    def normalize_types(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return cleaned or ["*"]


class WebhookEndpointUpdate(BaseModel):
    url: AnyHttpUrl | None = None
    description: str | None = Field(default=None, max_length=500)
    event_types: list[str] | None = None
    enabled: bool | None = None


class WebhookEndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    description: str
    event_types: list[str]
    enabled: bool
    secret_prefix: str = Field(description="First 8 chars of the signing secret (for support).")
    created_at: datetime


class WebhookEndpointCreated(WebhookEndpointRead):
    signing_secret: str = Field(
        description="Shown once. Use it to verify `X-Webhook-Signature` on your server."
    )


class WebhookEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=64, examples=["order.created"])
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str
    created_at: datetime


class WebhookDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    endpoint_id: int
    endpoint_url: str
    attempt_number: int
    status: DeliveryStatus
    http_status: int | None
    error_detail: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None
