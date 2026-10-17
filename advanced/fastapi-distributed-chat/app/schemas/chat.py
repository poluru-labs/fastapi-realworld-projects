from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RoomVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class RoomStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MemberRole(StrEnum):
    MEMBER = "member"
    MODERATOR = "moderator"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    DELIVERING = "delivering"
    DELIVERED = "delivered"


class RoomCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    visibility: RoomVisibility = RoomVisibility.PUBLIC


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    visibility: RoomVisibility
    status: RoomStatus
    owner_id: int
    message_sequence: int
    created_at: datetime
    updated_at: datetime


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    role: MemberRole
    last_read_sequence: int
    joined_at: datetime


class ReadCursorUpdate(BaseModel):
    last_read_sequence: int = Field(ge=0)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    author_id: int
    sequence: int
    body: str
    created_at: datetime


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    room_id: int
    recipient_id: int
    status: OutboxStatus
    lease_holder: str | None
    version: int
    delivered_at: datetime | None
    created_at: datetime


class RelayRegister(BaseModel):
    relay_id: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    room_slugs: list[str] = Field(default_factory=list, max_length=32)


class RelayHeartbeat(BaseModel):
    relay_id: str = Field(min_length=2, max_length=64)


class ClaimDeliveryRequest(BaseModel):
    relay_id: str = Field(min_length=2, max_length=64)


class CompleteDeliveryRequest(BaseModel):
    relay_id: str = Field(min_length=2, max_length=64)
    expected_version: int = Field(ge=1)
