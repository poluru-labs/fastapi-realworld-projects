from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.chat import MembershipRead, ReadCursorUpdate, RoomCreate, RoomRead, RoomUpdate
from app.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get(
    "",
    response_model=list[RoomRead],
    summary="List public active rooms",
    description="Discover rooms anyone may join. Private rooms never appear here.",
)
async def list_public_rooms(
    session: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[RoomRead]:
    _ = user
    return await RoomService(session).list_public(limit=limit, offset=offset)


@router.get(
    "/mine",
    response_model=list[RoomRead],
    summary="Rooms you belong to",
)
async def list_my_rooms(
    session: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[RoomRead]:
    return await RoomService(session).list_mine(user, limit=limit, offset=offset)


@router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    session: DbSession,
    user: CurrentUser,
) -> RoomRead:
    return await RoomService(session).create(user, payload)


@router.get("/{slug}", response_model=RoomRead)
async def get_room(slug: str, session: DbSession, user: CurrentUser) -> RoomRead:
    return await RoomService(session).get_room(user, slug)


@router.patch("/{slug}", response_model=RoomRead)
async def update_room(
    slug: str,
    payload: RoomUpdate,
    session: DbSession,
    user: CurrentUser,
) -> RoomRead:
    return await RoomService(session).update_room(user, slug, payload)


@router.post("/{slug}/join", response_model=MembershipRead)
async def join_room(slug: str, session: DbSession, user: CurrentUser) -> MembershipRead:
    return await RoomService(session).join(user, slug)


@router.post("/{slug}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room(slug: str, session: DbSession, user: CurrentUser) -> None:
    await RoomService(session).leave(user, slug)


@router.post("/{slug}/archive", response_model=RoomRead)
async def archive_room(slug: str, session: DbSession, user: CurrentUser) -> RoomRead:
    return await RoomService(session).archive(user, slug)


@router.get("/{slug}/members", response_model=list[MembershipRead])
async def list_members(slug: str, session: DbSession, user: CurrentUser) -> list[MembershipRead]:
    return await RoomService(session).list_members(user, slug)


@router.patch("/{slug}/members/me/read", response_model=MembershipRead)
async def update_read_cursor(
    slug: str,
    payload: ReadCursorUpdate,
    session: DbSession,
    user: CurrentUser,
) -> MembershipRead:
    return await RoomService(session).update_read_cursor(user, slug, payload)
