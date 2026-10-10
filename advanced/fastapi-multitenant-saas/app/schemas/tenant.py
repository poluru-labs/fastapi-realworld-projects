from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.tenant import TenantPlan


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    plan: TenantPlan
    is_active: bool
    created_at: datetime


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=2, max_length=80)

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str) -> str:
        import re

        slug = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            msg = "slug must be lowercase letters, numbers, and hyphens"
            raise ValueError(msg)
        return slug


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    plan: TenantPlan | None = None


class TenantMembershipSummary(BaseModel):
    tenant: TenantRead
    role: str
