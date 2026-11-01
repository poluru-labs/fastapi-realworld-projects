from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import TenantMembership, TenantRole
from app.models.tenant import Tenant


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, tenant_id: int, user_id: int) -> TenantMembership | None:
        result = await self._session.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, *, tenant_id: int, user_id: int, role: TenantRole) -> TenantMembership:
        row = TenantMembership(tenant_id=tenant_id, user_id=user_id, role=role.value)
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_user(self, user_id: int) -> list[tuple[Tenant, TenantMembership]]:
        result = await self._session.execute(
            select(Tenant, TenantMembership)
            .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
            .where(TenantMembership.user_id == user_id)
            .order_by(Tenant.slug)
        )
        return list(result.all())
