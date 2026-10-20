from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.message_repository import MessageRepository
from app.repositories.room_repository import MembershipRecord, RoomRecord, RoomRepository
from app.repositories.user_repository import UserRepository
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


def _can_view_room(actor: UserRead | None, room: RoomRecord, *, rooms: RoomRepository) -> bool:
    if room.status is RoomStatus.ARCHIVED:
        if actor is None:
            return False
        if actor.role is UserRole.ADMIN or actor.id == room.owner_id:
            return True
        return rooms.is_member(room.id, actor.id)
    if room.visibility is RoomVisibility.PUBLIC:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return rooms.is_member(room.id, actor.id)


class RoomService:
    def __init__(
        self,
        *,
        rooms: RoomRepository,
        messages: MessageRepository,
        users: UserRepository,
    ) -> None:
        self._rooms = rooms
        self._messages = messages
        self._users = users

    def list_discoverable(self, actor: UserRead | None) -> list[RoomRead]:
        rows = self._rooms.list_public_active()
        rows.sort(key=lambda room: room.slug)
        return [self._to_read(room) for room in rows]

    def get_room(self, actor: UserRead | None, slug: str) -> RoomRead:
        room = self._visible_room(actor, slug)
        return self._to_read(room)

    def create_room(self, actor: UserRead, payload: RoomCreate) -> RoomRead:
        if self._rooms.slug_taken(payload.slug):
            raise ConflictError("Another room already uses this slug")
        now = datetime.now(UTC)
        room = RoomRecord(
            id=self._rooms.allocate_id(),
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            visibility=payload.visibility,
            status=RoomStatus.ACTIVE,
            owner_id=actor.id,
            message_sequence=0,
            created_at=now,
            updated_at=now,
        )
        self._rooms.add(room)
        self._rooms.add_member(
            MembershipRecord(
                room_id=room.id,
                user_id=actor.id,
                role=MemberRole.MODERATOR,
                last_read_sequence=0,
                joined_at=now,
            )
        )
        return self._to_read(room)

    def update_room(self, actor: UserRead, slug: str, payload: RoomUpdate) -> RoomRead:
        room = self._visible_room(actor, slug)
        self._require_owner(actor, room)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            room.name = changes["name"]
        if "description" in changes and changes["description"] is not None:
            room.description = changes["description"]
        room.updated_at = datetime.now(UTC)
        self._rooms.save(room)
        return self._to_read(room)

    def invite_member(self, actor: UserRead, slug: str, user_id: int) -> MembershipRead:
        room = self._visible_room(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != room.owner_id:
            raise ForbiddenError("Only the owner or an admin can invite members")
        target = self._users.get_by_id(user_id)
        if target is None or not target.is_active:
            raise NotFoundError("User", user_id)
        if self._rooms.is_member(room.id, user_id):
            raise ConflictError("User is already a member")
        now = datetime.now(UTC)
        membership = MembershipRecord(
            room_id=room.id,
            user_id=user_id,
            role=MemberRole.MEMBER,
            last_read_sequence=room.message_sequence,
            joined_at=now,
        )
        self._rooms.add_member(membership)
        return MembershipRead(
            user_id=membership.user_id,
            full_name=target.full_name,
            role=membership.role,
            last_read_sequence=membership.last_read_sequence,
            joined_at=membership.joined_at,
        )

    def join_room(self, actor: UserRead, slug: str) -> RoomRead:
        room = self._visible_room(actor, slug)
        if room.status is not RoomStatus.ACTIVE:
            raise ConflictError("Cannot join an archived room")
        if room.visibility is not RoomVisibility.PUBLIC:
            raise ForbiddenError("Private rooms require an invitation from the owner")
        if self._rooms.is_member(room.id, actor.id):
            return self._to_read(room)
        now = datetime.now(UTC)
        self._rooms.add_member(
            MembershipRecord(
                room_id=room.id,
                user_id=actor.id,
                role=MemberRole.MEMBER,
                last_read_sequence=room.message_sequence,
                joined_at=now,
            )
        )
        return self._to_read(room)

    def list_members(self, actor: UserRead, slug: str) -> list[MembershipRead]:
        room = self._require_member_room(actor, slug)
        members = self._rooms.list_members(room.id)
        result: list[MembershipRead] = []
        for membership in members:
            user = self._users.get_by_id(membership.user_id)
            result.append(
                MembershipRead(
                    user_id=membership.user_id,
                    full_name=user.full_name if user is not None else "Unknown",
                    role=membership.role,
                    last_read_sequence=membership.last_read_sequence,
                    joined_at=membership.joined_at,
                )
            )
        result.sort(key=lambda row: row.joined_at)
        return result

    def update_read_cursor(
        self,
        actor: UserRead,
        slug: str,
        payload: ReadCursorUpdate,
    ) -> MembershipRead:
        room = self._require_member_room(actor, slug)
        membership = self._rooms.get_membership(room.id, actor.id)
        assert membership is not None
        if payload.last_read_sequence > room.message_sequence:
            raise ConflictError("Cannot read past the latest message sequence")
        membership.last_read_sequence = payload.last_read_sequence
        self._rooms.update_membership(membership)
        user = self._users.get_by_id(actor.id)
        return MembershipRead(
            user_id=membership.user_id,
            full_name=user.full_name if user is not None else actor.full_name,
            role=membership.role,
            last_read_sequence=membership.last_read_sequence,
            joined_at=membership.joined_at,
        )

    def archive_room(self, actor: UserRead, slug: str) -> RoomRead:
        room = self._visible_room(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != room.owner_id:
            raise ForbiddenError("Only the owner or an admin can archive this room")
        if room.status is RoomStatus.ARCHIVED:
            raise ConflictError("Room is already archived")
        room.status = RoomStatus.ARCHIVED
        room.updated_at = datetime.now(UTC)
        self._rooms.save(room)
        return self._to_read(room)

    def visible_room(self, actor: UserRead | None, slug: str) -> RoomRecord:
        return self._visible_room(actor, slug)

    def require_member_room(self, actor: UserRead, slug: str) -> RoomRecord:
        return self._require_member_room(actor, slug)

    def _visible_room(self, actor: UserRead | None, slug: str) -> RoomRecord:
        room = self._rooms.get_by_slug(slug)
        if room is None or not _can_view_room(actor, room, rooms=self._rooms):
            raise NotFoundError("Room", slug)
        return room

    def _require_member_room(self, actor: UserRead, slug: str) -> RoomRecord:
        room = self._visible_room(actor, slug)
        if actor.role is UserRole.ADMIN:
            return room
        if not self._rooms.is_member(room.id, actor.id):
            raise ForbiddenError("Join the room before reading or sending messages")
        return room

    def _require_owner(self, actor: UserRead, room: RoomRecord) -> None:
        if actor.id != room.owner_id:
            raise ForbiddenError("Only the room owner can edit metadata")

    def _to_read(self, room: RoomRecord) -> RoomRead:
        return RoomRead(
            id=room.id,
            slug=room.slug,
            name=room.name,
            description=room.description,
            visibility=room.visibility,
            status=room.status,
            owner_id=room.owner_id,
            message_sequence=room.message_sequence,
            member_count=self._rooms.member_count(room.id),
            created_at=room.created_at,
            updated_at=room.updated_at,
        )
