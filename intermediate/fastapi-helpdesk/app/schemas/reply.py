from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReplyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(
        ...,
        min_length=1,
        max_length=4_000,
        examples=["I tried the reset link twice; it expires immediately."],
    )


class ReplyRead(BaseModel):
    id: int
    ticket_id: int
    message: str
    author_id: int
    author_name: str
    created_at: datetime


class ReplyPage(BaseModel):
    items: list[ReplyRead]
    total: int
    limit: int
    offset: int
