from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.editor import Document, DocumentMembership
from app.models.user import User
from app.schemas.editor import DocumentStatus, DocumentVisibility, MemberRole
from app.schemas.user import UserRole


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Editor Admin",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

    playbook = await session.scalar(select(Document).where(Document.slug == "team-playbook"))
    if playbook is None:
        now = datetime.now(UTC)
        playbook = Document(
            slug="team-playbook",
            title="Team playbook",
            body="Hello team",
            revision=1,
            visibility=DocumentVisibility.PUBLIC.value,
            status=DocumentStatus.ACTIVE.value,
            owner_id=admin.id,
            created_at=now,
            updated_at=now,
        )
        session.add(playbook)
        await session.flush()
        session.add(
            DocumentMembership(
                document_id=playbook.id,
                user_id=admin.id,
                role=MemberRole.EDITOR.value,
                last_seen_revision=1,
            )
        )

    private = await session.scalar(select(Document).where(Document.slug == "private-design-doc"))
    if private is None:
        session.add(
            Document(
                slug="private-design-doc",
                title="Private design notes",
                body="",
                revision=0,
                visibility=DocumentVisibility.PRIVATE.value,
                status=DocumentStatus.ACTIVE.value,
                owner_id=admin.id,
            )
        )
        await session.flush()
        private_row = await session.scalar(
            select(Document).where(Document.slug == "private-design-doc")
        )
        if private_row is not None:
            session.add(
                DocumentMembership(
                    document_id=private_row.id,
                    user_id=admin.id,
                    role=MemberRole.EDITOR.value,
                )
            )

    await session.commit()
