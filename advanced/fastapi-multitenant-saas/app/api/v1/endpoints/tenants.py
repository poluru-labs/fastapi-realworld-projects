from fastapi import APIRouter, status

from app.api.deps import ActiveTenant, CurrentUser, DbSession
from app.schemas.membership import MemberInvite, MemberWithUser
from app.schemas.tenant import TenantCreate, TenantMembershipSummary, TenantRead, TenantUpdate
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get(
    "/mine",
    response_model=list[TenantMembershipSummary],
    summary="Tenants the caller belongs to",
)
async def list_my_tenants(user: CurrentUser, session: DbSession) -> list[TenantMembershipSummary]:
    return await TenantService(session).list_mine(user.id)


@router.post(
    "",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create another tenant (caller becomes owner)",
)
async def create_tenant(
    payload: TenantCreate,
    user: CurrentUser,
    session: DbSession,
) -> TenantRead:
    return await TenantService(session).create_tenant(user.id, payload)


@router.get(
    "/current",
    response_model=TenantRead,
    summary="Resolve tenant from X-Tenant-Slug",
    description=(
        "Requires `Authorization` and **`X-Tenant-Slug`** — "
        "the active workspace for this request."
    ),
)
async def read_current_tenant(ctx: ActiveTenant) -> TenantRead:
    return ctx.tenant


@router.patch(
    "/current",
    response_model=TenantRead,
    summary="Update tenant metadata (admin+)",
)
async def update_current_tenant(
    payload: TenantUpdate,
    ctx: ActiveTenant,
    session: DbSession,
) -> TenantRead:
    return await TenantService(session).update_current(
        tenant_id=ctx.tenant.id,
        actor_role=ctx.role,
        payload=payload,
    )


@router.get(
    "/current/members",
    response_model=list[MemberWithUser],
    summary="List members in the active tenant",
)
async def list_members(ctx: ActiveTenant, session: DbSession) -> list[MemberWithUser]:
    return await TenantService(session).list_members(tenant_id=ctx.tenant.id, actor_role=ctx.role)


@router.post(
    "/current/members",
    response_model=MemberWithUser,
    status_code=status.HTTP_201_CREATED,
    summary="Invite an existing user by email (admin+)",
)
async def invite_member(
    payload: MemberInvite,
    ctx: ActiveTenant,
    session: DbSession,
) -> MemberWithUser:
    return await TenantService(session).invite_member(
        tenant_id=ctx.tenant.id,
        actor_role=ctx.role,
        payload=payload,
    )


@router.delete(
    "/current/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member (admin+; owner rules apply)",
)
async def remove_member(
    user_id: int,
    ctx: ActiveTenant,
    user: CurrentUser,
    session: DbSession,
) -> None:
    await TenantService(session).remove_member(
        tenant_id=ctx.tenant.id,
        actor_id=user.id,
        actor_role=ctx.role,
        target_user_id=user_id,
    )
