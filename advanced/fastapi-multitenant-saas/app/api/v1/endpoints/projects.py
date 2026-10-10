from fastapi import APIRouter, status

from app.api.deps import ActiveTenant, AppSettings, DbSession
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "",
    response_model=list[ProjectRead],
    summary="List projects in the active tenant",
    description=(
        "Every query is scoped by **`X-Tenant-Slug`** — "
        "rows from other tenants are never returned."
    ),
)
async def list_projects(
    ctx: ActiveTenant,
    session: DbSession,
    settings: AppSettings,
) -> list[ProjectRead]:
    return await ProjectService(session, settings).list_projects(ctx.tenant.id)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant-scoped project",
    description=(
        "Free plan tenants hit **409** after `FREE_PLAN_PROJECT_LIMIT` projects "
        "(see settings)."
    ),
)
async def create_project(
    payload: ProjectCreate,
    ctx: ActiveTenant,
    session: DbSession,
    settings: AppSettings,
) -> ProjectRead:
    return await ProjectService(session, settings).create_project(ctx.tenant.id, payload)


@router.get("/{project_id}", response_model=ProjectRead, summary="Get one project")
async def get_project(
    project_id: int,
    ctx: ActiveTenant,
    session: DbSession,
    settings: AppSettings,
) -> ProjectRead:
    return await ProjectService(session, settings).get_project(
        tenant_id=ctx.tenant.id,
        project_id=project_id,
    )


@router.patch("/{project_id}", response_model=ProjectRead, summary="Update project fields")
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    ctx: ActiveTenant,
    session: DbSession,
    settings: AppSettings,
) -> ProjectRead:
    return await ProjectService(session, settings).update_project(
        tenant_id=ctx.tenant.id,
        project_id=project_id,
        payload=payload,
        actor_role=ctx.role,
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project (admin+)",
)
async def delete_project(
    project_id: int,
    ctx: ActiveTenant,
    session: DbSession,
    settings: AppSettings,
) -> None:
    await ProjectService(session, settings).delete_project(
        tenant_id=ctx.tenant.id,
        project_id=project_id,
        actor_role=ctx.role,
    )
