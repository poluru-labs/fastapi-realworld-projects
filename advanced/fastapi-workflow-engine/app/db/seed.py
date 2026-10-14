from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.workflow import WorkflowDefinition
from app.schemas.user import UserRole
from app.schemas.workflow import DefinitionStatus

_ONBOARDING_TRANSITIONS = [
    {
        "action": "complete_profile",
        "from": "invite_sent",
        "to": "profile_complete",
    },
    {
        "action": "approve",
        "from": "profile_complete",
        "to": "manager_approved",
        "roles": ["admin"],
    },
    {
        "action": "activate",
        "from": "manager_approved",
        "to": "active",
        "roles": ["admin"],
    },
]


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Workflow Admin",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

    published = await session.scalar(
        select(WorkflowDefinition).where(WorkflowDefinition.slug == "employee-onboarding")
    )
    if published is None:
        session.add(
            WorkflowDefinition(
                slug="employee-onboarding",
                name="Employee onboarding",
                description="Invite → profile → manager approval → active account.",
                status=DefinitionStatus.PUBLISHED.value,
                initial_state="invite_sent",
                states=[
                    "invite_sent",
                    "profile_complete",
                    "manager_approved",
                    "active",
                ],
                transitions=_ONBOARDING_TRANSITIONS,
                terminal_states=["active"],
            )
        )

    draft = await session.scalar(
        select(WorkflowDefinition).where(WorkflowDefinition.slug == "draft-internal")
    )
    if draft is None:
        session.add(
            WorkflowDefinition(
                slug="draft-internal",
                name="Internal draft workflow",
                description="Hidden until published.",
                status=DefinitionStatus.DRAFT.value,
                initial_state="start",
                states=["start", "done"],
                transitions=[{"action": "finish", "from": "start", "to": "done"}],
                terminal_states=["done"],
            )
        )

    await session.commit()
