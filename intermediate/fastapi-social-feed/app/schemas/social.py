from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class FollowCounts(BaseModel):
    followers: int = Field(description="Accounts that follow this user.")
    following: int = Field(description="Accounts this user follows.")


class UserPublicProfile(BaseModel):
    user: UserRead
    counts: FollowCounts
    followed_by_me: bool = Field(
        description="Whether the caller follows this account. False when anonymous."
    )


class FollowList(BaseModel):
    items: list[UserRead]
    total: int
