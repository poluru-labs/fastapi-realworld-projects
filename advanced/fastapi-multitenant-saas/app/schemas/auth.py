import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    """Creates a global user account and a new tenant where they are owner."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    tenant_name: str = Field(min_length=1, max_length=120)
    tenant_slug: str = Field(min_length=2, max_length=80)

    @field_validator("tenant_slug")
    @classmethod
    def slug_format(cls, value: str) -> str:
        slug = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            msg = "tenant_slug must be lowercase letters, numbers, and hyphens"
            raise ValueError(msg)
        return slug


class RegisterResponse(BaseModel):
    user: "UserRead"
    tenant: "TenantRead"
    tokens: TokenPair


from app.schemas.tenant import TenantRead  # noqa: E402
from app.schemas.user import UserRead  # noqa: E402

RegisterResponse.model_rebuild()
