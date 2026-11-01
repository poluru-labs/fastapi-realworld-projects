from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_workflow import AgentStepLog, AgentWorkflowDefinition, AgentWorkflowRun


class AgentWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(
            select(AgentWorkflowDefinition.id).where(AgentWorkflowDefinition.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def get_definition_by_slug(self, slug: str) -> AgentWorkflowDefinition | None:
        result = await self._session.execute(
            select(AgentWorkflowDefinition).where(AgentWorkflowDefinition.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_definitions(self) -> list[AgentWorkflowDefinition]:
        result = await self._session.scalars(
            select(AgentWorkflowDefinition).order_by(AgentWorkflowDefinition.slug)
        )
        return list(result)

    async def add_definition(self, row: AgentWorkflowDefinition) -> AgentWorkflowDefinition:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_run(self, run_id: int) -> AgentWorkflowRun | None:
        return await self._session.get(AgentWorkflowRun, run_id)

    async def get_run_by_idempotency(self, key: str) -> AgentWorkflowRun | None:
        return await self._session.scalar(
            select(AgentWorkflowRun).where(AgentWorkflowRun.idempotency_key == key)
        )

    async def list_runs(self, *, limit: int, offset: int) -> list[AgentWorkflowRun]:
        result = await self._session.scalars(
            select(AgentWorkflowRun)
            .order_by(AgentWorkflowRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def add_run(self, run: AgentWorkflowRun) -> AgentWorkflowRun:
        self._session.add(run)
        await self._session.flush()
        return run

    async def add_step_logs(self, logs: list[AgentStepLog]) -> None:
        self._session.add_all(logs)
        await self._session.flush()

    async def list_step_logs(self, run_id: int) -> list[AgentStepLog]:
        result = await self._session.scalars(
            select(AgentStepLog)
            .where(AgentStepLog.run_id == run_id)
            .order_by(AgentStepLog.sequence)
        )
        return list(result)
