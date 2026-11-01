from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(select(Tenant.id).where(Tenant.slug == slug))
        return result.scalar_one_or_none() is not None

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, slug: str) -> Tenant:
        tenant = Tenant(name=name, slug=slug.lower())
        self._session.add(tenant)
        await self._session.flush()
        return tenant
