from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class TeamRole(StrEnum):
    """Membership on one team. Separate from the platform role on the user."""

    OWNER = "owner"
    MEMBER = "member"


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, examples=["Design"])
    description: str = Field("", max_length=500)


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    description: str | None = Field(None, max_length=500)


class TeamRead(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    member_count: int
    team_role: TeamRole | None = Field(
        None,
        description=(
            "Your membership on this team. Null when a platform admin "
            "views a team they have not joined."
        ),
    )
    created_at: datetime


class MemberAdd(BaseModel):
    email: EmailStr = Field(..., examples=["dev@example.com"])


class MemberRead(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    team_role: TeamRole
