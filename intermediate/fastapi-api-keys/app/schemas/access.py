from pydantic import BaseModel, Field

from app.schemas.api_key import ApiKeyScope


class WhoamiRead(BaseModel):
    auth_method: str = Field(description="`jwt` or `api_key`")
    user_id: int
    email: str
    api_key_id: int | None = None
    api_key_prefix: str | None = None
    scopes: list[ApiKeyScope] = Field(default_factory=list)


class MetricsRead(BaseModel):
    project_count: int
    active_api_keys: int
