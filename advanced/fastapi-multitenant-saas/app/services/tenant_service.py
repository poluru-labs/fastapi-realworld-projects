from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.membership import TenantRole
from app.repositories.membership_repository import MembershipRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.membership import MemberInvite, MembershipRead, MemberWithUser
from app.schemas.tenant import TenantCreate, TenantMembershipSummary, TenantRead, TenantUpdate
from app.schemas.user import UserPublic

_ROLE_RANK = {
    TenantRole.MEMBER: 1,
    TenantRole.ADMIN: 2,
    TenantRole.OWNER: 3,
}


def _require_role(*, actual: TenantRole, minimum: TenantRole) -> None:
    if _ROLE_RANK[actual] < _ROLE_RANK[minimum]:
        raise ForbiddenError()


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tenants = TenantRepository(session)
        self._memberships = MembershipRepository(session)
        self._users = UserRepository(session)

    async def list_mine(self, user_id: int) -> list[TenantMembershipSummary]:
        rows = await self._memberships.list_for_user(user_id)
        return [
            TenantMembershipSummary(
                tenant=TenantRead.model_validate(tenant),
                role=membership.role,
            )
            for membership, tenant in rows
            if tenant.is_active
        ]

    async def create_tenant(self, user_id: int, payload: TenantCreate) -> TenantRead:
        if await self._tenants.slug_exists(payload.slug):
            raise ConflictError("Tenant slug already taken")
        tenant = await self._tenants.create(name=payload.name, slug=payload.slug)
        await self._memberships.create(
            tenant_id=tenant.id,
            user_id=user_id,
            role=TenantRole.OWNER,
        )
        await self._session.commit()
        return TenantRead.model_validate(tenant)

    async def update_current(
        self,
        *,
        tenant_id: int,
        actor_role: TenantRole,
        payload: TenantUpdate,
    ) -> TenantRead:
        _require_role(actual=actor_role, minimum=TenantRole.ADMIN)
        tenant = await self._tenants.get_by_id(tenant_id)
        if tenant is None or not tenant.is_active:
            raise NotFoundError("Tenant", tenant_id)
        updated = await self._tenants.update(tenant, name=payload.name, plan=payload.plan)
        await self._session.commit()
        return TenantRead.model_validate(updated)

    async def list_members(
        self,
        *,
        tenant_id: int,
        actor_role: TenantRole,
    ) -> list[MemberWithUser]:
        _require_role(actual=actor_role, minimum=TenantRole.MEMBER)
        rows = await self._memberships.list_for_tenant(tenant_id)
        return [
            MemberWithUser(
                membership=MembershipRead.model_validate(membership),
                user=UserPublic.model_validate(user),
            )
            for membership, user in rows
        ]

    async def invite_member(
        self,
        *,
        tenant_id: int,
        actor_role: TenantRole,
        payload: MemberInvite,
    ) -> MemberWithUser:
        _require_role(actual=actor_role, minimum=TenantRole.ADMIN)
        if payload.role == TenantRole.OWNER:
            raise ForbiddenError("Cannot assign owner via invite")

        user = await self._users.get_by_email(payload.email)
        if user is None:
            raise NotFoundError("User", payload.email)

        existing = await self._memberships.get(tenant_id=tenant_id, user_id=user.id)
        if existing is not None:
            raise ConflictError("User is already a member of this tenant")

        membership = await self._memberships.create(
            tenant_id=tenant_id,
            user_id=user.id,
            role=payload.role,
        )
        await self._session.commit()
        return MemberWithUser(
            membership=MembershipRead.model_validate(membership),
            user=UserPublic.model_validate(user),
        )

    async def remove_member(
        self,
        *,
        tenant_id: int,
        actor_id: int,
        actor_role: TenantRole,
        target_user_id: int,
    ) -> None:
        _require_role(actual=actor_role, minimum=TenantRole.ADMIN)
        target = await self._memberships.get(tenant_id=tenant_id, user_id=target_user_id)
        if target is None:
            raise NotFoundError("Member", target_user_id)

        target_role = TenantRole(target.role)
        if target_role == TenantRole.OWNER:
            owners = await self._memberships.count_owners(tenant_id)
            if owners <= 1:
                raise ConflictError("Cannot remove the last owner")
            raise ForbiddenError("Only an owner can remove another owner")

        if target_user_id == actor_id and target_role == TenantRole.OWNER:
            raise ConflictError("Transfer ownership before leaving as owner")

        await self._memberships.delete(target)
        await self._session.commit()
