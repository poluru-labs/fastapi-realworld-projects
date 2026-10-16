from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cover_letter: str = Field(
        ...,
        min_length=1,
        max_length=2_000,
        examples=["I have shipped FastAPI services in production for three years."],
    )


class ApplicationRead(BaseModel):
    id: int
    job_id: int
    cover_letter: str
    status: ApplicationStatus
    applicant_id: int
    applicant_name: str
    created_at: datetime


class ApplicationPage(BaseModel):
    items: list[ApplicationRead]
    total: int
    limit: int
    offset: int
