from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    is_active: bool
    created_at: datetime


class TenantMineRead(BaseModel):
    tenant: TenantRead
    role: str
