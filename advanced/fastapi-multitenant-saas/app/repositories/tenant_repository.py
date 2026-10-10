from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantPlan


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(select(Tenant.id).where(Tenant.slug == slug))
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, tenant_id: int) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, slug: str, plan: TenantPlan = TenantPlan.FREE) -> Tenant:
        tenant = Tenant(name=name, slug=slug, plan=plan.value)
        self._session.add(tenant)
        await self._session.flush()
        return tenant

    async def update(self, tenant: Tenant, *, name: str | None, plan: TenantPlan | None) -> Tenant:
        if name is not None:
            tenant.name = name
        if plan is not None:
            tenant.plan = plan.value
        await self._session.flush()
        return tenant
