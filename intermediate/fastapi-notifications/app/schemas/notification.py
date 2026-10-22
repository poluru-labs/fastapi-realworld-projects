from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationType(StrEnum):
    SYSTEM = "system"
    MENTION = "mention"
    REMINDER = "reminder"
    BILLING = "billing"


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: NotificationType
    title: str
    body: str
    data: dict[str, Any] = Field(default_factory=dict)
    read_at: datetime | None
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int
    limit: int
    offset: int


class UnreadCount(BaseModel):
    unread: int


class NotificationDispatch(BaseModel):
    user_id: int = Field(..., ge=1)
    type: NotificationType = NotificationType.SYSTEM
    title: str = Field(..., min_length=1, max_length=160)
    body: str = Field(..., min_length=1, max_length=2000)
    data: dict[str, Any] = Field(default_factory=dict)


class NotificationPreferencesRead(BaseModel):
    marketing_email: bool
    product_email: bool
    push_enabled: bool


class NotificationPreferencesUpdate(BaseModel):
    marketing_email: bool | None = None
    product_email: bool | None = None
    push_enabled: bool | None = None
