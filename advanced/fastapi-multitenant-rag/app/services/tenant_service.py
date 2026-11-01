from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.membership_repository import MembershipRepository
from app.schemas.tenant import TenantMineRead, TenantRead


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self._memberships = MembershipRepository(session)

    async def list_mine(self, user_id: int) -> list[TenantMineRead]:
        rows = await self._memberships.list_for_user(user_id)
        return [
            TenantMineRead(
                tenant=TenantRead.model_validate(tenant),
                role=membership.role,
            )
            for tenant, membership in rows
        ]
