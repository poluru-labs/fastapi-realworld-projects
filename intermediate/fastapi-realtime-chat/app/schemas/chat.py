import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class RoomVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class RoomStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MemberRole(StrEnum):
    MEMBER = "member"
    MODERATOR = "moderator"


class RoomCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slug: str = Field(..., min_length=2, max_length=64, examples=["project-alpha"])
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    visibility: RoomVisibility = Field(
        default=RoomVisibility.PUBLIC,
        description="Public rooms appear in discovery. Private rooms are 404 to non-members.",
    )

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, slug: str) -> str:
        slug = slug.casefold()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return slug


class RoomRead(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    visibility: RoomVisibility
    status: RoomStatus
    owner_id: int
    message_sequence: int = Field(description="Monotonic counter; last assigned sequence number.")
    member_count: int
    created_at: datetime
    updated_at: datetime


class RoomUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class MembershipRead(BaseModel):
    user_id: int
    full_name: str
    role: MemberRole
    last_read_sequence: int
    joined_at: datetime


class ReadCursorUpdate(BaseModel):
    last_read_sequence: int = Field(ge=0, description="Highest message sequence you have consumed.")


class MessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    body: str = Field(..., min_length=1, max_length=4000)


class MessageRead(BaseModel):
    id: int
    room_id: int
    author_id: int
    author_name: str
    sequence: int
    body: str
    created_at: datetime


class MessagePage(BaseModel):
    items: list[MessageRead]
    room_slug: str
    after_sequence: int
    latest_sequence: int


class WsEvent(BaseModel):
    """Shape pushed over the room WebSocket after REST sends."""

    type: str = Field(default="message", examples=["message"])
    payload: MessageRead
