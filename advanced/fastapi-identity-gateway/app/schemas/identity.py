from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class GrantType(StrEnum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"


class OAuthScope(StrEnum):
    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    API_READ = "api:read"
    API_WRITE = "api:write"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grant_types: list[GrantType] = Field(min_length=1, max_length=3)
    allowed_scopes: list[OAuthScope] = Field(min_length=1, max_length=10)
    redirect_uris: list[str] = Field(default_factory=list, max_length=5)
    is_confidential: bool = True

    @model_validator(mode="after")
    def redirect_required_for_code(self) -> "ClientCreate":
        if GrantType.AUTHORIZATION_CODE in self.grant_types and not self.redirect_uris:
            raise ValueError("redirect_uris required when authorization_code grant is enabled")
        return self


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: str
    name: str
    grant_types: list[str]
    allowed_scopes: list[str]
    redirect_uris: list[str]
    is_confidential: bool
    created_at: datetime


class ClientCreated(BaseModel):
    client: ClientRead
    client_secret: str


class AuthorizeRequest(BaseModel):
    client_id: str = Field(min_length=4, max_length=64)
    redirect_uri: str = Field(min_length=1, max_length=500)
    scope: str = Field(default="openid profile", max_length=500)
    state: str | None = Field(default=None, max_length=128)


class AuthorizeResponse(BaseModel):
    code: str
    state: str | None
    expires_in: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    refresh_token: str | None = None


class IntrospectRequest(BaseModel):
    token: str = Field(min_length=10)


class IntrospectResponse(BaseModel):
    active: bool
    sub: str | None = None
    client_id: str | None = None
    scope: str | None = None
    exp: int | None = None
    token_type: str | None = None


class UserInfoResponse(BaseModel):
    sub: str
    email: EmailStr | None = None
    name: str | None = None
    client_id: str
    scope: str
