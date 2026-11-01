from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PolicyEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class ClearanceLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SECRET = "secret"


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
    clearance: ClearanceLevel
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str


class RoleAssignment(BaseModel):
    email: EmailStr
    role_slug: str = Field(min_length=2, max_length=32)


class PolicyRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    effect: PolicyEffect
    actions: list[str] = Field(min_length=1, max_length=20)
    resources: list[str] = Field(min_length=1, max_length=20)
    roles: list[str] = Field(default_factory=list, max_length=10)
    required_clearance: ClearanceLevel | None = None
    priority: int = Field(default=100, ge=1, le=1000)
    description: str = Field(default="", max_length=2000)


class PolicyRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    effect: PolicyEffect
    actions: list[str]
    resources: list[str]
    roles: list[str]
    required_clearance: ClearanceLevel | None
    priority: int
    description: str
    created_at: datetime


class EvaluateRequest(BaseModel):
    action: str = Field(min_length=3, max_length=64)
    resource: str = Field(min_length=1, max_length=200)
    resource_attributes: dict[str, Any] = Field(default_factory=dict)


class EvaluateResponse(BaseModel):
    allowed: bool
    matched_rule: str | None
    action: str
    resource: str


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    classification: ClearanceLevel = ClearanceLevel.INTERNAL
    body: str = Field(default="", max_length=50_000)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    classification: ClearanceLevel
    body: str
    created_at: datetime


class WhoAmI(BaseModel):
    user: UserRead
    message: str = "Use POST /policy/evaluate to debug decisions before hitting protected routes."
