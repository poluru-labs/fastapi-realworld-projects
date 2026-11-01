from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class ProjectRead(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime
