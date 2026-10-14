from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowDefinition, WorkflowEvent, WorkflowInstance


class WorkflowDefinitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> WorkflowDefinition | None:
        stmt = select(WorkflowDefinition).where(WorkflowDefinition.slug == slug)
        return await self._session.scalar(stmt)

    async def get_by_id(self, definition_id: int) -> WorkflowDefinition | None:
        return await self._session.get(WorkflowDefinition, definition_id)

    async def list_all(self) -> list[WorkflowDefinition]:
        stmt = select(WorkflowDefinition).order_by(WorkflowDefinition.slug)
        return list(await self._session.scalars(stmt))

    async def slug_taken(self, slug: str) -> bool:
        return await self.get_by_slug(slug) is not None

    async def add(self, row: WorkflowDefinition) -> WorkflowDefinition:
        self._session.add(row)
        await self._session.flush()
        return row


class WorkflowInstanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, instance_id: int) -> WorkflowInstance | None:
        return await self._session.get(WorkflowInstance, instance_id)

    async def get_for_update(self, instance_id: int) -> WorkflowInstance | None:
        stmt = (
            select(WorkflowInstance)
            .where(WorkflowInstance.id == instance_id)
            .with_for_update()
        )
        return await self._session.scalar(stmt)

    async def list_for_owner(self, owner_id: int) -> list[WorkflowInstance]:
        stmt = (
            select(WorkflowInstance)
            .where(WorkflowInstance.owner_id == owner_id)
            .order_by(WorkflowInstance.id.desc())
        )
        return list(await self._session.scalars(stmt))

    async def list_all(self) -> list[WorkflowInstance]:
        stmt = select(WorkflowInstance).order_by(WorkflowInstance.id.desc())
        return list(await self._session.scalars(stmt))

    async def add(self, row: WorkflowInstance) -> WorkflowInstance:
        self._session.add(row)
        await self._session.flush()
        return row

    async def append_event(self, event: WorkflowEvent) -> None:
        self._session.add(event)

    async def list_events(self, instance_id: int) -> list[WorkflowEvent]:
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.instance_id == instance_id)
            .order_by(WorkflowEvent.sequence)
        )
        return list(await self._session.scalars(stmt))
