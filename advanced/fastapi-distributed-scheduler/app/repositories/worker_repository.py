from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduler import WorkerNode


class WorkerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, worker_id: str) -> WorkerNode | None:
        return await self._session.get(WorkerNode, worker_id)

    async def upsert(
        self,
        *,
        worker_id: str,
        registered_by_id: int,
        capabilities: list[str],
        now: datetime,
    ) -> WorkerNode:
        node = await self.get(worker_id)
        if node is None:
            node = WorkerNode(
                worker_id=worker_id,
                registered_by_id=registered_by_id,
                capabilities=capabilities,
                last_heartbeat_at=now,
            )
            self._session.add(node)
        else:
            node.capabilities = capabilities
            node.last_heartbeat_at = now
        await self._session.flush()
        return node

    async def heartbeat(self, worker_id: str, now: datetime) -> WorkerNode | None:
        node = await self.get(worker_id)
        if node is None:
            return None
        node.last_heartbeat_at = now
        await self._session.flush()
        return node
