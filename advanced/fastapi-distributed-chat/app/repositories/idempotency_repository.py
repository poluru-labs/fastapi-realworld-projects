from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> IdempotencyRecord | None:
        return await self._session.get(IdempotencyRecord, key)

    async def save(
        self,
        *,
        key: str,
        user_id: int,
        response_json: str,
        status_code: int = 201,
    ) -> None:
        self._session.add(
            IdempotencyRecord(
                key=key,
                user_id=user_id,
                response_json=response_json,
                status_code=status_code,
            )
        )
