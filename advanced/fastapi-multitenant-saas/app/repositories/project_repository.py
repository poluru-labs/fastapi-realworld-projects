from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_for_tenant(self, tenant_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Project).where(Project.tenant_id == tenant_id)
        )
        return int(result.scalar_one())

    async def list_for_tenant(self, tenant_id: int) -> list[Project]:
        result = await self._session.execute(
            select(Project).where(Project.tenant_id == tenant_id).order_by(Project.name)
        )
        return list(result.scalars().all())

    async def get_for_tenant(self, *, tenant_id: int, project_id: int) -> Project | None:
        result = await self._session.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create(self, *, tenant_id: int, name: str, description: str) -> Project:
        project = Project(tenant_id=tenant_id, name=name, description=description)
        self._session.add(project)
        await self._session.flush()
        return project

    async def update(
        self,
        project: Project,
        *,
        name: str | None,
        description: str | None,
    ) -> Project:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        project.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        await self._session.delete(project)
