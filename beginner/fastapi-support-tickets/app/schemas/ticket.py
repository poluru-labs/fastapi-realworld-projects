from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "subject": "Cannot reset password",
                    "description": "The reset link expires immediately after I open it.",
                    "requester_email": "customer@example.com",
                    "priority": "high",
                }
            ]
        },
    )

    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=8000)
    requester_email: EmailStr
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    priority: TicketPriority | None = None
    assignee: str | None = Field(default=None, max_length=120)
    status: TicketStatus | None = None


class TicketRead(BaseModel):
    id: int
    subject: str
    description: str
    requester_email: EmailStr
    priority: TicketPriority
    status: TicketStatus
    assignee: str | None
    comment_count: int
    created_at: datetime
    updated_at: datetime


class CommentCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "author_name": "Support Agent",
                    "body": "We reproduced the issue and escalated to engineering.",
                    "is_internal": False,
                }
            ]
        },
    )

    author_name: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., min_length=1, max_length=4000)
    is_internal: bool = False


class CommentRead(BaseModel):
    id: int
    ticket_id: int
    author_name: str
    body: str
    is_internal: bool
    created_at: datetime


class TicketDetail(TicketRead):
    comments: list[CommentRead]
