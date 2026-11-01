from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImageRead(BaseModel):
    id: int
    filename: str
    content_type: str
    format: str
    width: int
    height: int
    size_bytes: int
    caption: str
    tags: list[str]
    content_path: str
    uploaded_at: datetime


class ImageUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    caption: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=20)
