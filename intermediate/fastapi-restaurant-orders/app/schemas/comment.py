from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    body: str = Field(
        ...,
        min_length=1,
        max_length=2_000,
        examples=["The 404 on a draft is the interesting part."],
    )


class CommentRead(BaseModel):
    id: int
    post_id: int
    body: str
    author_id: int
    author_name: str
    created_at: datetime


class CommentPage(BaseModel):
    items: list[CommentRead]
    total: int = Field(description="Comments on this post before limit and offset.")
    limit: int
    offset: int
