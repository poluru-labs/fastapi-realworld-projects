from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import TenantMembership, TenantRole
from app.models.tenant import Tenant
from app.models.user import User


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

    async def create(
        self,
        *,
        tenant_id: int,
        user_id: int,
        role: TenantRole,
    ) -> TenantMembership:
        membership = TenantMembership(tenant_id=tenant_id, user_id=user_id, role=role.value)
        self._session.add(membership)
        await self._session.flush()
        return membership

    async def list_for_tenant(self, tenant_id: int) -> list[tuple[TenantMembership, User]]:
        result = await self._session.execute(
            select(TenantMembership, User)
            .join(User, User.id == TenantMembership.user_id)
            .where(TenantMembership.tenant_id == tenant_id)
            .order_by(TenantMembership.created_at)
        )
        return list(result.all())

    async def list_for_user(self, user_id: int) -> list[tuple[TenantMembership, Tenant]]:
        result = await self._session.execute(
            select(TenantMembership, Tenant)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .where(TenantMembership.user_id == user_id)
            .order_by(Tenant.name)
        )
        return list(result.all())

    async def delete(self, membership: TenantMembership) -> None:
        await self._session.delete(membership)

    async def count_owners(self, tenant_id: int) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.role == TenantRole.OWNER.value,
            )
        )
        return int(result.scalar_one())
