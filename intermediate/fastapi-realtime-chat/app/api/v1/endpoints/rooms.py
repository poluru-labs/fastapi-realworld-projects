from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import get_current_user, get_optional_user, get_room_service
from app.schemas.chat import (
    SLUG_PATTERN,
    MembershipRead,
    ReadCursorUpdate,
    RoomCreate,
    RoomRead,
    RoomUpdate,
)
from app.schemas.user import UserRead
from app.services.room_service import RoomService

router = APIRouter()

Slug = Annotated[
    str,
    Path(pattern=SLUG_PATTERN.pattern, min_length=2, max_length=64, examples=["general"]),
]

_OPTIONAL_BEARER = {"security": [{}, {"OAuth2PasswordBearer": []}]}


@router.get(
    "",
    response_model=list[RoomRead],
    summary="Discover public rooms",
    description="Active public rooms only. Private channels never appear here.",
    openapi_extra=_OPTIONAL_BEARER,
)
def list_rooms(
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> list[RoomRead]:
    return service.list_discoverable(actor)


@router.post(
    "",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a room",
    description="Creator becomes moderator and the owner. Slugs are immutable.",
)
def create_room(
    payload: RoomCreate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> RoomRead:
    return service.create_room(actor, payload)


@router.get(
    "/{slug}",
    response_model=RoomRead,
    summary="Room metadata",
    description=(
        "Public active rooms need no token. Private and archived rooms follow the "
        "same 404 privacy pattern as other intermediate APIs."
    ),
    openapi_extra=_OPTIONAL_BEARER,
)
def get_room(
    slug: Slug,
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> RoomRead:
    return service.get_room(actor, slug)


@router.patch(
    "/{slug}",
    response_model=RoomRead,
    summary="Update room metadata",
    description="Owner only.",
)
def update_room(
    slug: Slug,
    payload: RoomUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> RoomRead:
    return service.update_room(actor, slug, payload)


@router.post(
    "/{slug}/join",
    response_model=RoomRead,
    summary="Join a public room",
    description="Private rooms return 403; use invite instead.",
)
def join_room(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> RoomRead:
    return service.join_room(actor, slug)


@router.post(
    "/{slug}/invite/{user_id}",
    response_model=MembershipRead,
    summary="Invite a user to a private room",
    description=(
        "Owner or platform admin. Also works for public rooms when you want explicit membership."
    ),
)
def invite_member(
    slug: Slug,
    user_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> MembershipRead:
    return service.invite_member(actor, slug, user_id)


@router.get(
    "/{slug}/members",
    response_model=list[MembershipRead],
    summary="List members",
    description="Requires membership (or admin).",
)
def list_members(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> list[MembershipRead]:
    return service.list_members(actor, slug)


@router.put(
    "/{slug}/read-cursor",
    response_model=MembershipRead,
    summary="Update read cursor",
    description="Store the highest message sequence you have consumed.",
)
def update_read_cursor(
    slug: Slug,
    payload: ReadCursorUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> MembershipRead:
    return service.update_read_cursor(actor, slug, payload)


@router.post(
    "/{slug}/archive",
    response_model=RoomRead,
    summary="Archive a room",
    description="Owner or admin. Archived rooms reject new messages.",
)
def archive_room(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RoomService, Depends(get_room_service)],
) -> RoomRead:
    return service.archive_room(actor, slug)
