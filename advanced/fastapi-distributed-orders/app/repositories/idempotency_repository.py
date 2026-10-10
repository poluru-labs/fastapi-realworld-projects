from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> IdempotencyRecord | None:
        return await self._session.get(IdempotencyRecord, key)

    async def save(self, record: IdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()
