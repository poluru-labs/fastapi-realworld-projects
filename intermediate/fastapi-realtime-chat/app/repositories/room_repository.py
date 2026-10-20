from dataclasses import dataclass
from datetime import datetime

from app.schemas.chat import MemberRole, RoomStatus, RoomVisibility


@dataclass
class RoomRecord:
    id: int
    slug: str
    name: str
    description: str
    visibility: RoomVisibility
    status: RoomStatus
    owner_id: int
    message_sequence: int
    created_at: datetime
    updated_at: datetime


@dataclass
class MembershipRecord:
    room_id: int
    user_id: int
    role: MemberRole
    last_read_sequence: int
    joined_at: datetime


def _seed_rooms() -> dict[int, RoomRecord]:
    created = datetime.fromisoformat("2026-03-01T12:00:00+00:00")
    return {
        1: RoomRecord(
            id=1,
            slug="general",
            name="General",
            description="Open channel for demos. Join, send REST messages, watch the WebSocket.",
            visibility=RoomVisibility.PUBLIC,
            status=RoomStatus.ACTIVE,
            owner_id=1,
            message_sequence=1,
            created_at=created,
            updated_at=created,
        ),
        2: RoomRecord(
            id=2,
            slug="team-leads",
            name="Team leads",
            description="Private room seeded for admin only.",
            visibility=RoomVisibility.PRIVATE,
            status=RoomStatus.ACTIVE,
            owner_id=1,
            message_sequence=0,
            created_at=created,
            updated_at=created,
        ),
    }


def _seed_memberships() -> list[MembershipRecord]:
    joined = datetime.fromisoformat("2026-03-01T12:00:00+00:00")
    return [
        MembershipRecord(
            room_id=1,
            user_id=1,
            role=MemberRole.MODERATOR,
            last_read_sequence=1,
            joined_at=joined,
        ),
        MembershipRecord(
            room_id=2,
            user_id=1,
            role=MemberRole.MODERATOR,
            last_read_sequence=0,
            joined_at=joined,
        ),
    ]


class RoomRepository:
    def __init__(self) -> None:
        self._by_id = dict(_seed_rooms())
        self._by_slug = {room.slug: room for room in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1
        self._memberships: list[MembershipRecord] = list(_seed_memberships())

    def list_all(self) -> list[RoomRecord]:
        return list(self._by_id.values())

    def list_public_active(self) -> list[RoomRecord]:
        return [
            room
            for room in self._by_id.values()
            if room.visibility is RoomVisibility.PUBLIC and room.status is RoomStatus.ACTIVE
        ]

    def get_by_slug(self, slug: str) -> RoomRecord | None:
        return self._by_slug.get(slug)

    def get_by_id(self, room_id: int) -> RoomRecord | None:
        return self._by_id.get(room_id)

    def slug_taken(self, slug: str) -> bool:
        return slug in self._by_slug

    def allocate_id(self) -> int:
        room_id = self._next_id
        self._next_id += 1
        return room_id

    def add(self, record: RoomRecord) -> RoomRecord:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: RoomRecord) -> None:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record

    def is_member(self, room_id: int, user_id: int) -> bool:
        return any(m.room_id == room_id and m.user_id == user_id for m in self._memberships)

    def list_members(self, room_id: int) -> list[MembershipRecord]:
        return [m for m in self._memberships if m.room_id == room_id]

    def member_count(self, room_id: int) -> int:
        return len(self.list_members(room_id))

    def get_membership(self, room_id: int, user_id: int) -> MembershipRecord | None:
        for membership in self._memberships:
            if membership.room_id == room_id and membership.user_id == user_id:
                return membership
        return None

    def add_member(self, membership: MembershipRecord) -> None:
        if self.get_membership(membership.room_id, membership.user_id) is not None:
            return
        self._memberships.append(membership)

    def update_membership(self, membership: MembershipRecord) -> None:
        for index, existing in enumerate(self._memberships):
            if existing.room_id == membership.room_id and existing.user_id == membership.user_id:
                self._memberships[index] = membership
                return
