from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="At least 8 characters.")
    full_name: str = Field(..., min_length=1, max_length=120)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole = Field(
        description="Platform role. Admin manages events and sees every registration."
    )
    is_active: bool
