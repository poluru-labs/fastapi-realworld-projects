import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

CODE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


class LinkCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "target_url": "https://fastapi.tiangolo.com/tutorial/",
                    "title": "FastAPI tutorial",
                    "custom_code": "fastapi",
                }
            ]
        },
    )

    target_url: HttpUrl
    title: str = Field(default="", max_length=200)
    custom_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        pattern=CODE_PATTERN.pattern,
        description="Optional vanity code; auto-generated when omitted.",
    )


class LinkUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    target_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class LinkRead(BaseModel):
    id: int
    code: str
    target_url: str
    title: str
    click_count: int
    is_active: bool
    redirect_path: str
    created_at: datetime
