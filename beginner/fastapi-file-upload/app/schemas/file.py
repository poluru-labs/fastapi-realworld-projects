from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileRead(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    description: str
    download_path: str
    uploaded_at: datetime


class FileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str | None = Field(default=None, max_length=500)
