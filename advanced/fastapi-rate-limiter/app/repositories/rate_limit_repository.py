from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_limiting import (
    RateLimitClient,
    RateLimitCounter,
    RateLimitIdempotencyRecord,
    RateLimitPolicy,
)


class RateLimitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_policies(self) -> list[RateLimitPolicy]:
        result = await self._session.scalars(select(RateLimitPolicy).order_by(RateLimitPolicy.key))
        return list(result)

    async def get_policy_by_key(self, key: str) -> RateLimitPolicy | None:
        return await self._session.scalar(select(RateLimitPolicy).where(RateLimitPolicy.key == key))

    async def get_policy_by_id(self, policy_id: int) -> RateLimitPolicy | None:
        return await self._session.get(RateLimitPolicy, policy_id)

    async def add_policy(self, policy: RateLimitPolicy) -> RateLimitPolicy:
        self._session.add(policy)
        await self._session.flush()
        return policy

    async def list_clients(self) -> list[RateLimitClient]:
        result = await self._session.scalars(select(RateLimitClient).order_by(RateLimitClient.key))
        return list(result)

    async def get_client_by_key(self, key: str) -> RateLimitClient | None:
        return await self._session.scalar(select(RateLimitClient).where(RateLimitClient.key == key))

    async def add_client(self, client: RateLimitClient) -> RateLimitClient:
        self._session.add(client)
        await self._session.flush()
        return client

    async def get_counter(
        self,
        client_id: int,
        subject_key: str,
        window_start: datetime,
    ) -> RateLimitCounter | None:
        return await self._session.scalar(
            select(RateLimitCounter).where(
                RateLimitCounter.client_id == client_id,
                RateLimitCounter.subject_key == subject_key,
                RateLimitCounter.window_start == window_start,
            )
        )

    async def get_or_create_counter(
        self,
        client_id: int,
        subject_key: str,
        window_start: datetime,
    ) -> RateLimitCounter:
        counter = await self.get_counter(client_id, subject_key, window_start)
        if counter is not None:
            return counter
        counter = RateLimitCounter(
            client_id=client_id,
            subject_key=subject_key,
            window_start=window_start,
            count=0,
        )
        self._session.add(counter)
        await self._session.flush()
        return counter

    async def list_counters_for_client(
        self,
        client_id: int,
        window_start: datetime,
    ) -> list[RateLimitCounter]:
        result = await self._session.scalars(
            select(RateLimitCounter).where(
                RateLimitCounter.client_id == client_id,
                RateLimitCounter.window_start == window_start,
            )
        )
        return list(result)

    async def get_idempotency(
        self,
        client_id: int,
        idempotency_key: str,
    ) -> RateLimitIdempotencyRecord | None:
        return await self._session.scalar(
            select(RateLimitIdempotencyRecord).where(
                RateLimitIdempotencyRecord.client_id == client_id,
                RateLimitIdempotencyRecord.idempotency_key == idempotency_key,
            )
        )

    async def add_idempotency(self, record: RateLimitIdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()
