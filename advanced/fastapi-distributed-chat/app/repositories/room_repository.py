from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRoom, RoomMembership


class RoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> ChatRoom | None:
        stmt = select(ChatRoom).where(ChatRoom.slug == slug)
        return await self._session.scalar(stmt)

    async def get_by_id(self, room_id: int) -> ChatRoom | None:
        return await self._session.get(ChatRoom, room_id)

    async def list_public(self, *, limit: int, offset: int) -> list[ChatRoom]:
        rows = await self._session.scalars(
            select(ChatRoom)
            .where(
                ChatRoom.visibility == "public",
                ChatRoom.status == "active",
            )
            .order_by(ChatRoom.name)
            .limit(limit)
            .offset(offset)
        )
        return list(rows)

    async def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[ChatRoom]:
        rows = await self._session.scalars(
            select(ChatRoom)
            .join(RoomMembership, RoomMembership.room_id == ChatRoom.id)
            .where(RoomMembership.user_id == user_id, ChatRoom.status == "active")
            .order_by(ChatRoom.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows)

    async def add(self, room: ChatRoom) -> ChatRoom:
        self._session.add(room)
        await self._session.flush()
        return room

    async def membership(self, *, room_id: int, user_id: int) -> RoomMembership | None:
        stmt = select(RoomMembership).where(
            RoomMembership.room_id == room_id,
            RoomMembership.user_id == user_id,
        )
        return await self._session.scalar(stmt)

    async def list_members(self, room_id: int) -> list[RoomMembership]:
        rows = await self._session.scalars(
            select(RoomMembership).where(RoomMembership.room_id == room_id)
        )
        return list(rows)

    async def add_member(self, membership: RoomMembership) -> RoomMembership:
        self._session.add(membership)
        await self._session.flush()
        return membership

    async def save(self) -> None:
        await self._session.flush()
