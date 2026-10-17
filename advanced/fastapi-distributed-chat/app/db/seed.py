from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.chat import ChatMessage, ChatRoom, RoomMembership
from app.models.user import User
from app.schemas.chat import MemberRole, RoomStatus, RoomVisibility
from app.schemas.user import UserRole


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Chat Admin",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

    general = await session.scalar(select(ChatRoom).where(ChatRoom.slug == "general"))
    if general is None:
        now = datetime.now(UTC)
        general = ChatRoom(
            slug="general",
            name="General",
            description="Public room for trying message sync and relay delivery.",
            visibility=RoomVisibility.PUBLIC.value,
            status=RoomStatus.ACTIVE.value,
            owner_id=admin.id,
            message_sequence=1,
            created_at=now,
            updated_at=now,
        )
        session.add(general)
        await session.flush()
        session.add(
            RoomMembership(
                room_id=general.id,
                user_id=admin.id,
                role=MemberRole.MODERATOR.value,
                last_read_sequence=1,
            )
        )
        session.add(
            ChatMessage(
                room_id=general.id,
                author_id=admin.id,
                sequence=1,
                body="Welcome to distributed chat — send a message with Idempotency-Key.",
                created_at=now,
            )
        )

    private_ops = await session.scalar(select(ChatRoom).where(ChatRoom.slug == "private-ops"))
    if private_ops is None:
        session.add(
            ChatRoom(
                slug="private-ops",
                name="Private ops",
                description="Visible only to members; returns 404 to everyone else.",
                visibility=RoomVisibility.PRIVATE.value,
                status=RoomStatus.ACTIVE.value,
                owner_id=admin.id,
                message_sequence=0,
            )
        )
        await session.flush()
        private_row = await session.scalar(select(ChatRoom).where(ChatRoom.slug == "private-ops"))
        if private_row is not None:
            session.add(
                RoomMembership(
                    room_id=private_row.id,
                    user_id=admin.id,
                    role=MemberRole.MODERATOR.value,
                )
            )

    await session.commit()
