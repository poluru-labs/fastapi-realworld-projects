from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_user_service, require_roles
from app.core.exceptions import ForbiddenError
from app.schemas.user import UserRead, UserRole
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=list[UserRead],
    summary="List accounts",
    description="Platform admin only.",
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
