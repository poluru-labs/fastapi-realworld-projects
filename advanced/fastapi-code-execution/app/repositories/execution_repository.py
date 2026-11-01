from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import ExecutionPolicy, ExecutionRun


class ExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_policy(self) -> ExecutionPolicy | None:
        return await self._session.get(ExecutionPolicy, 1)

    async def save_policy(self, policy: ExecutionPolicy) -> ExecutionPolicy:
        self._session.add(policy)
        await self._session.flush()
        return policy

    async def get_run(self, run_id: int) -> ExecutionRun | None:
        return await self._session.get(ExecutionRun, run_id)

    async def get_run_by_idempotency(self, key: str) -> ExecutionRun | None:
        return await self._session.scalar(
            select(ExecutionRun).where(ExecutionRun.idempotency_key == key)
        )

    async def list_runs(self, *, limit: int, offset: int) -> list[ExecutionRun]:
        result = await self._session.scalars(
            select(ExecutionRun).order_by(ExecutionRun.id.desc()).limit(limit).offset(offset)
        )
        return list(result)

    async def add_run(self, run: ExecutionRun) -> ExecutionRun:
        self._session.add(run)
        await self._session.flush()
        return run
