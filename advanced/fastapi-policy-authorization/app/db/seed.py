from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.policy import Document, PolicyRule, Role, User, UserRole
from app.schemas.policy import ClearanceLevel, PolicyEffect

SEED_VIEWER_EMAIL = "viewer@example.com"
SEED_EDITOR_EMAIL = "editor@example.com"
SEED_PASSWORD = "DemoPass123!"


async def seed_reference_data(session: AsyncSession) -> None:
    if await session.scalar(select(Role.id).limit(1)) is not None:
        return

    roles = {
        "admin": Role(slug="admin", name="Administrator"),
        "editor": Role(slug="editor", name="Editor"),
        "viewer": Role(slug="viewer", name="Viewer"),
    }
    session.add_all(roles.values())
    await session.flush()

    editor = User(
        email=SEED_EDITOR_EMAIL,
        hashed_password=hash_password(SEED_PASSWORD),
        full_name="Ed Editor",
        clearance=ClearanceLevel.INTERNAL.value,
    )
    viewer = User(
        email=SEED_VIEWER_EMAIL,
        hashed_password=hash_password(SEED_PASSWORD),
        full_name="Vi Viewer",
        clearance=ClearanceLevel.PUBLIC.value,
    )
    session.add_all([editor, viewer])
    await session.flush()

    session.add_all(
        [
            UserRole(user_id=editor.id, role_id=roles["editor"].id),
            UserRole(user_id=viewer.id, role_id=roles["viewer"].id),
        ]
    )

    session.add_all(
        [
            PolicyRule(
                name="editors-manage-documents",
                effect=PolicyEffect.ALLOW.value,
                actions=["documents:*"],
                resources=["document/*"],
                roles=["editor", "admin"],
                required_clearance=None,
                priority=200,
                description="Editors may read and create documents.",
            ),
            PolicyRule(
                name="viewers-read-documents",
                effect=PolicyEffect.ALLOW.value,
                actions=["documents:read"],
                resources=["document/*"],
                roles=["viewer"],
                required_clearance=None,
                priority=150,
                description="Viewers read when their clearance covers document classification.",
            ),
        ]
    )

    session.add_all(
        [
            Document(
                owner_id=editor.id,
                title="Public FAQ",
                classification=ClearanceLevel.PUBLIC.value,
                body="General information.",
            ),
            Document(
                owner_id=editor.id,
                title="Internal roadmap",
                classification=ClearanceLevel.INTERNAL.value,
                body="Q4 milestones.",
            ),
            Document(
                owner_id=editor.id,
                title="Secret acquisition plan",
                classification=ClearanceLevel.SECRET.value,
                body="Confidential.",
            ),
        ]
    )
    await session.commit()
