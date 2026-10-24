from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.rate_limiting import RateLimitPolicy
from app.repositories.rate_limit_repository import RateLimitRepository
from app.schemas.rate_limiting import PolicyCreate, PolicyRead, PolicyStatus


class PolicyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RateLimitRepository(session)

    async def list_policies(self) -> list[PolicyRead]:
        rows = await self._repo.list_policies()
        return [self._read(row) for row in rows]

    async def create_policy(self, payload: PolicyCreate) -> PolicyRead:
        if await self._repo.get_policy_by_key(payload.key) is not None:
            raise ConflictError(f"Policy key {payload.key!r} already exists")
        now = datetime.now(UTC)
        policy = RateLimitPolicy(
            key=payload.key,
            name=payload.name,
            description=payload.description,
            limit=payload.limit,
            window_seconds=payload.window_seconds,
            status=PolicyStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        await self._repo.add_policy(policy)
        await self._session.commit()
        return self._read(policy)

    async def get_policy(self, policy_key: str) -> PolicyRead:
        policy = await self._require_policy(policy_key)
        return self._read(policy)

    async def pause_policy(self, policy_key: str) -> PolicyRead:
        policy = await self._require_policy(policy_key)
        if policy.status == PolicyStatus.PAUSED.value:
            raise ConflictError("Policy is already paused")
        policy.status = PolicyStatus.PAUSED.value
        policy.updated_at = datetime.now(UTC)
        await self._session.commit()
        return self._read(policy)

    async def resume_policy(self, policy_key: str) -> PolicyRead:
        policy = await self._require_policy(policy_key)
        if policy.status == PolicyStatus.ACTIVE.value:
            raise ConflictError("Policy is already active")
        policy.status = PolicyStatus.ACTIVE.value
        policy.updated_at = datetime.now(UTC)
        await self._session.commit()
        return self._read(policy)

    async def _require_policy(self, policy_key: str) -> RateLimitPolicy:
        policy = await self._repo.get_policy_by_key(policy_key)
        if policy is None:
            raise NotFoundError("Policy", policy_key)
        return policy

    @staticmethod
    def _read(policy: RateLimitPolicy) -> PolicyRead:
        return PolicyRead(
            id=policy.id,
            key=policy.key,
            name=policy.name,
            description=policy.description,
            limit=policy.limit,
            window_seconds=policy.window_seconds,
            status=PolicyStatus(policy.status),
        )
