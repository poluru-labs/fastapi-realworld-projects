from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RegistrationStatus(StrEnum):
    REGISTERED = "registered"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


class RegistrationCreate(BaseModel):
    event_slug: str = Field(..., min_length=1, max_length=80, examples=["fastapi-meetup"])


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    event_slug: str
    event_title: str
    user_id: int
    attendee_name: str
    status: RegistrationStatus
    created_at: datetime
