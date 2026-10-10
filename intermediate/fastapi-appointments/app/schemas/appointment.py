from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


MIN_DURATION_MINUTES = 15
MAX_DURATION_HOURS = 8


class AppointmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: int = Field(..., ge=1, examples=[1])
    title: str = Field(..., min_length=1, max_length=120, examples=["Annual checkup"])
    notes: str = Field(default="", max_length=500)
    starts_at: datetime = Field(..., description="ISO-8601 datetime with timezone offset.")
    ends_at: datetime = Field(..., description="Must be after starts_at.")

    @model_validator(mode="after")
    def validate_window(self) -> "AppointmentCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        delta = self.ends_at - self.starts_at
        minutes = delta.total_seconds() / 60
        if minutes < MIN_DURATION_MINUTES:
            raise ValueError(f"Appointments must be at least {MIN_DURATION_MINUTES} minutes")
        if minutes > MAX_DURATION_HOURS * 60:
            raise ValueError(f"Appointments cannot exceed {MAX_DURATION_HOURS} hours")
        return self


class AppointmentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_partial_window(self) -> "AppointmentUpdate":
        if self.starts_at is not None and self.ends_at is not None:
            if self.ends_at <= self.starts_at:
                raise ValueError("ends_at must be after starts_at")
        return self


class AppointmentRead(BaseModel):
    id: int
    user_id: int
    client_name: str
    provider_id: int
    provider_name: str
    title: str
    notes: str
    status: AppointmentStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime
