from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class EventStatus(StrEnum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class EventCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "FastAPI study group",
                    "description": "Bring your laptop and work through /docs together.",
                    "location": "Library room B",
                    "starts_at": "2026-04-15T18:00:00+00:00",
                    "ends_at": "2026-04-15T20:00:00+00:00",
                    "max_attendees": 25,
                }
            ]
        },
    )

    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    location: str = Field(..., min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime
    max_attendees: int | None = Field(default=None, ge=1, le=100_000)

    @model_validator(mode="after")
    def end_after_start(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_attendees: int | None = Field(default=None, ge=1, le=100_000)


class EventRead(BaseModel):
    id: int
    title: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    status: EventStatus
    max_attendees: int | None
    registration_count: int


class RegistrationCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Alex Rivera",
                    "email": "alex@example.com",
                }
            ]
        },
    )

    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr


class RegistrationRead(BaseModel):
    id: int
    event_id: int
    name: str
    email: EmailStr
    registered_at: datetime


class EventDetail(EventRead):
    registrations: list[RegistrationRead]
