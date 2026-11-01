from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class MockCatalog(StrEnum):
    USERS = "users"
    ORDERS = "orders"
    INVENTORY = "inventory"


class SourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slug: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    base_url: HttpUrl
    mock_catalog: MockCatalog
    description: str = Field(default="", max_length=500)


class SourceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class SourceRead(BaseModel):
    id: int
    slug: str
    display_name: str
    base_url: str
    mock_catalog: MockCatalog
    description: str
    is_active: bool
    owner_id: int
    created_at: datetime
