from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_follow_service,
    get_optional_user,
    get_user_service,
    require_roles,
)
from app.core.exceptions import ForbiddenError
from app.schemas.social import FollowCounts, FollowList, UserPublicProfile
from app.schemas.user import UserRead, UserRole
from app.services.follow_service import FollowService
from app.services.user_service import UserService

router = APIRouter()

_OPTIONAL_BEARER = {"security": [{}, {"OAuth2PasswordBearer": []}]}


@router.get(
    "",
    response_model=list[UserRead],
    summary="List accounts",
    description="Platform admin only. Authors do not need this to publish.",
    responses={403: {"description": "The caller is signed in but is not an admin."}},
)
def list_users(
    _: Annotated[UserRead, Depends(require_roles(UserRole.ADMIN))],
    service: Annotated[UserService, Depends(get_user_service)],
) -> list[UserRead]:
    return service.list_users()


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Read one account",
    description="You can read your own account. A platform admin can read any account.",
    responses={
        403: {"description": "You asked for someone else's account."},
        404: {"description": "No account with this id."},
    },
)
def get_user(
    user_id: int,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise ForbiddenError("You can only view your own profile")
    return service.get_user(user_id)


@router.get(
    "/{user_id}/profile",
    response_model=UserPublicProfile,
    summary="Public profile with follow counts",
    description=(
        "Anyone can read follower counts. Send a token to learn whether you follow this account."
    ),
    openapi_extra=_OPTIONAL_BEARER,
)
def public_profile(
    user_id: int,
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    service: Annotated[FollowService, Depends(get_follow_service)],
) -> UserPublicProfile:
    return service.profile(actor, user_id)


@router.get(
    "/{user_id}/followers",
    response_model=FollowList,
    summary="List followers",
    description="Accounts that follow this user. No token required.",
)
def list_followers(
    user_id: int,
    service: Annotated[FollowService, Depends(get_follow_service)],
) -> FollowList:
    return service.list_followers(user_id)


@router.get(
    "/{user_id}/following",
    response_model=FollowList,
    summary="List following",
    description="Accounts this user follows. No token required.",
)
def list_following(
    user_id: int,
    service: Annotated[FollowService, Depends(get_follow_service)],
) -> FollowList:
    return service.list_following(user_id)


@router.post(
    "/{user_id}/follow",
    response_model=FollowCounts,
    status_code=status.HTTP_200_OK,
    summary="Follow an account",
    description="You cannot follow yourself. Duplicate follows return 409.",
    responses={
        404: {"description": "No active account with this id."},
        409: {"description": "Already following or self-follow."},
    },
)
def follow_user(
    user_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FollowService, Depends(get_follow_service)],
) -> FollowCounts:
    return service.follow(actor, user_id)


@router.delete(
    "/{user_id}/follow",
    response_model=FollowCounts,
    summary="Unfollow an account",
    responses={409: {"description": "You were not following this account."}},
)
def unfollow_user(
    user_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FollowService, Depends(get_follow_service)],
) -> FollowCounts:
    return service.unfollow(actor, user_id)
