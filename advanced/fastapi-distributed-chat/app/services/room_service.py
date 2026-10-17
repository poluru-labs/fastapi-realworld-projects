from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.chat import ChatRoom, RoomMembership
from app.repositories.room_repository import RoomRepository
from app.schemas.chat import (
    MemberRole,
    MembershipRead,
    ReadCursorUpdate,
    RoomCreate,
    RoomRead,
    RoomStatus,
    RoomUpdate,
    RoomVisibility,
)
from app.schemas.user import UserRead, UserRole


class RoomService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rooms = RoomRepository(session)

    async def list_public(self, *, limit: int, offset: int) -> list[RoomRead]:
        rows = await self._rooms.list_public(limit=limit, offset=offset)
        return [RoomRead.model_validate(row) for row in rows]

    async def list_mine(self, actor: UserRead, *, limit: int, offset: int) -> list[RoomRead]:
        rows = await self._rooms.list_for_user(actor.id, limit=limit, offset=offset)
        return [RoomRead.model_validate(row) for row in rows]

    async def create(self, actor: UserRead, payload: RoomCreate) -> RoomRead:
        if await self._rooms.get_by_slug(payload.slug) is not None:
            raise ConflictError("Room slug already exists")
        now = datetime.now(UTC)
        room = ChatRoom(
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            visibility=payload.visibility.value,
            status=RoomStatus.ACTIVE.value,
            owner_id=actor.id,
            message_sequence=0,
            created_at=now,
            updated_at=now,
        )
        await self._rooms.add(room)
        await self._rooms.add_member(
            RoomMembership(
                room_id=room.id,
                user_id=actor.id,
                role=MemberRole.MODERATOR.value,
                last_read_sequence=0,
            )
        )
        await self._session.commit()
        return RoomRead.model_validate(room)

    async def get_room(self, actor: UserRead, slug: str) -> RoomRead:
        room = await self._require_visible_room(actor, slug)
        return RoomRead.model_validate(room)

    async def update_room(
        self,
        actor: UserRead,
        slug: str,
        payload: RoomUpdate,
    ) -> RoomRead:
        room = await self._require_visible_room(actor, slug)
        membership = await self._rooms.membership(room_id=room.id, user_id=actor.id)
        is_mod = membership is not None and membership.role == MemberRole.MODERATOR.value
        if actor.role is not UserRole.ADMIN and actor.id != room.owner_id and not is_mod:
            raise ForbiddenError("Only moderators or the owner can update this room")
        if payload.name is not None:
            room.name = payload.name
        if payload.description is not None:
            room.description = payload.description
        room.updated_at = datetime.now(UTC)
        await self._rooms.save()
        await self._session.commit()
        return RoomRead.model_validate(room)

    async def join(self, actor: UserRead, slug: str) -> MembershipRead:
        room = await self._rooms.get_by_slug(slug)
        if room is None or room.status != RoomStatus.ACTIVE.value:
            raise NotFoundError("Room", slug)
        if room.visibility != RoomVisibility.PUBLIC.value:
            raise NotFoundError("Room", slug)
        existing = await self._rooms.membership(room_id=room.id, user_id=actor.id)
        if existing is not None:
            return MembershipRead.model_validate(existing)
        membership = RoomMembership(
            room_id=room.id,
            user_id=actor.id,
            role=MemberRole.MEMBER.value,
        )
        await self._rooms.add_member(membership)
        await self._session.commit()
        return MembershipRead.model_validate(membership)

    async def leave(self, actor: UserRead, slug: str) -> None:
        room = await self._require_visible_room(actor, slug)
        if room.owner_id == actor.id:
            raise ConflictError("Room owner cannot leave; archive the room or transfer ownership")
        membership = await self._rooms.membership(room_id=room.id, user_id=actor.id)
        if membership is None:
            raise NotFoundError("Membership", slug)
        await self._session.delete(membership)
        await self._session.commit()

    async def archive(self, actor: UserRead, slug: str) -> RoomRead:
        room = await self._require_visible_room(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != room.owner_id:
            raise ForbiddenError("Only the owner or an admin can archive a room")
        if room.status == RoomStatus.ARCHIVED.value:
            raise ConflictError("Room is already archived")
        room.status = RoomStatus.ARCHIVED.value
        room.updated_at = datetime.now(UTC)
        await self._rooms.save()
        await self._session.commit()
        return RoomRead.model_validate(room)

    async def list_members(self, actor: UserRead, slug: str) -> list[MembershipRead]:
        room = await self._require_visible_room(actor, slug)
        members = await self._rooms.list_members(room.id)
        return [MembershipRead.model_validate(row) for row in members]

    async def update_read_cursor(
        self,
        actor: UserRead,
        slug: str,
        payload: ReadCursorUpdate,
    ) -> MembershipRead:
        room = await self._require_visible_room(actor, slug)
        membership = await self._rooms.membership(room_id=room.id, user_id=actor.id)
        if membership is None:
            raise NotFoundError("Membership", slug)
        if payload.last_read_sequence > room.message_sequence:
            raise ConflictError("Cannot read past the latest message sequence")
        membership.last_read_sequence = payload.last_read_sequence
        await self._rooms.save()
        await self._session.commit()
        return MembershipRead.model_validate(membership)

    async def require_member_room(self, actor: UserRead, slug: str) -> ChatRoom:
        room = await self._require_visible_room(actor, slug)
        membership = await self._rooms.membership(room_id=room.id, user_id=actor.id)
        if membership is None:
            raise NotFoundError("Room", slug)
        if room.status == RoomStatus.ARCHIVED.value:
            raise ConflictError("Room is archived")
        return room

    async def _require_visible_room(self, actor: UserRead, slug: str) -> ChatRoom:
        room = await self._rooms.get_by_slug(slug)
        if room is None:
            raise NotFoundError("Room", slug)
        if room.visibility == RoomVisibility.PRIVATE.value:
            membership = await self._rooms.membership(room_id=room.id, user_id=actor.id)
            if actor.role is not UserRole.ADMIN and membership is None:
                raise NotFoundError("Room", slug)
        return room
