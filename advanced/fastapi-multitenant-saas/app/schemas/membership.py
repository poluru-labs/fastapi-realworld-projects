from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.membership import TenantRole
from app.schemas.user import UserPublic


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    user_id: int
    role: TenantRole
    created_at: datetime


class MemberWithUser(BaseModel):
    membership: MembershipRead
    user: UserPublic


class MemberInvite(BaseModel):
    email: EmailStr
    role: TenantRole = TenantRole.MEMBER
