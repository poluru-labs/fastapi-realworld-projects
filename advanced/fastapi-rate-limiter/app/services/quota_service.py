from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.windows import fixed_window_reset_at, fixed_window_start
from app.models.rate_limiting import RateLimitClient, RateLimitIdempotencyRecord
from app.repositories.rate_limit_repository import RateLimitRepository
from app.schemas.rate_limiting import PolicyStatus, QuotaRequest, QuotaStatus


class QuotaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RateLimitRepository(session)

    async def check(self, client: RateLimitClient, payload: QuotaRequest) -> QuotaStatus:
        return await self._evaluate(client, payload, consume=False)

    async def consume(
        self,
        client: RateLimitClient,
        idempotency_key: str,
        payload: QuotaRequest,
    ) -> tuple[QuotaStatus, int]:
        cached = await self._repo.get_idempotency(client.id, idempotency_key)
        if cached is not None:
            body = QuotaStatus.model_validate_json(cached.response_json)
            return body, cached.status_code

        status = await self._evaluate(client, payload, consume=True)
        http_code = 200 if status.allowed else 429
        await self._repo.add_idempotency(
            RateLimitIdempotencyRecord(
                client_id=client.id,
                idempotency_key=idempotency_key,
                response_json=status.model_dump_json(),
                status_code=http_code,
            )
        )
        await self._session.commit()
        return status, http_code

    async def _evaluate(
        self,
        client: RateLimitClient,
        payload: QuotaRequest,
        *,
        consume: bool,
    ) -> QuotaStatus:
        policy = await self._repo.get_policy_by_id(client.policy_id)
        if policy is None:
            raise NotFoundError("Policy", client.policy_id)

        now = datetime.now(UTC)
        window_start = fixed_window_start(now, policy.window_seconds)
        reset_at = fixed_window_reset_at(window_start, policy.window_seconds)
        counter = await self._repo.get_or_create_counter(
            client.id,
            payload.subject_key,
            window_start,
        )

        current = counter.count
        paused = policy.status == PolicyStatus.PAUSED.value
        allowed = (not paused) and (current + payload.cost <= policy.limit)

        if consume and allowed:
            counter.count = current + payload.cost
            await self._session.flush()
            current = counter.count

        remaining = max(0, policy.limit - current)
        if not consume:
            allowed = (not paused) and (current + payload.cost <= policy.limit)
            remaining = max(0, policy.limit - current)

        return QuotaStatus(
            allowed=allowed,
            limit=policy.limit,
            remaining=remaining,
            reset_at=reset_at,
            policy_key=policy.key,
            client_key=client.key,
            subject_key=payload.subject_key,
            window_count=current,
        )
