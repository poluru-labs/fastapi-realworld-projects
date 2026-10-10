from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.membership import TenantRole
from app.models.tenant import TenantPlan
from app.repositories.project_repository import ProjectRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._projects = ProjectRepository(session)
        self._tenants = TenantRepository(session)

    async def list_projects(self, tenant_id: int) -> list[ProjectRead]:
        rows = await self._projects.list_for_tenant(tenant_id)
        return [ProjectRead.model_validate(row) for row in rows]

    async def create_project(self, tenant_id: int, payload: ProjectCreate) -> ProjectRead:
        tenant = await self._tenants.get_by_id(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant", tenant_id)

        if tenant.plan == TenantPlan.FREE.value:
            count = await self._projects.count_for_tenant(tenant_id)
            if count >= self._settings.free_plan_project_limit:
                raise ConflictError(
                    f"Free plan allows at most {self._settings.free_plan_project_limit} projects"
                )

        project = await self._projects.create(
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
        )
        await self._session.commit()
        return ProjectRead.model_validate(project)

    async def get_project(self, *, tenant_id: int, project_id: int) -> ProjectRead:
        project = await self._projects.get_for_tenant(tenant_id=tenant_id, project_id=project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        return ProjectRead.model_validate(project)

    async def update_project(
        self,
        *,
        tenant_id: int,
        project_id: int,
        payload: ProjectUpdate,
        actor_role: TenantRole,
    ) -> ProjectRead:
        project = await self._projects.get_for_tenant(tenant_id=tenant_id, project_id=project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        updated = await self._projects.update(
            project,
            name=payload.name,
            description=payload.description,
        )
        await self._session.commit()
        return ProjectRead.model_validate(updated)

    async def delete_project(
        self,
        *,
        tenant_id: int,
        project_id: int,
        actor_role: TenantRole,
    ) -> None:
        if actor_role == TenantRole.MEMBER:
            raise ConflictError("Members cannot delete projects; ask an admin")
        project = await self._projects.get_for_tenant(tenant_id=tenant_id, project_id=project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        await self._projects.delete(project)
        await self._session.commit()
