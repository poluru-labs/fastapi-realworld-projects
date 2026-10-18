from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.editor import SyncNode


class SyncNodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, node_id: str) -> SyncNode | None:
        return await self._session.get(SyncNode, node_id)

    async def upsert(
        self,
        *,
        node_id: str,
        registered_by_id: int,
        document_slugs: list[str],
        now: datetime,
    ) -> None:
        node = await self.get(node_id)
        if node is None:
            self._session.add(
                SyncNode(
                    node_id=node_id,
                    registered_by_id=registered_by_id,
                    document_slugs=document_slugs,
                    last_heartbeat_at=now,
                )
            )
        else:
            node.registered_by_id = registered_by_id
            node.document_slugs = document_slugs
            node.last_heartbeat_at = now
        await self._session.flush()

    async def heartbeat(self, node_id: str, now: datetime) -> None:
        node = await self.get(node_id)
        if node is not None:
            node.last_heartbeat_at = now
            await self._session.flush()
