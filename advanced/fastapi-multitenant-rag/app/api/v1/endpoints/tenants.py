from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.tenant import TenantMineRead
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get(
    "/mine",
    response_model=list[TenantMineRead],
    summary="List my tenants",
    description="Use a tenant `slug` as `X-Tenant-Slug` when calling collection and query APIs.",
)
async def list_my_tenants(user: CurrentUser, session: DbSession) -> list[TenantMineRead]:
    return await TenantService(session).list_mine(user.id)
