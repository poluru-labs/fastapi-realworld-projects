from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import RelayNode


class RelayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, relay_id: str) -> RelayNode | None:
        return await self._session.get(RelayNode, relay_id)

    async def upsert(
        self,
        *,
        relay_id: str,
        registered_by_id: int,
        room_slugs: list[str],
        now: datetime,
    ) -> None:
        node = await self.get(relay_id)
        if node is None:
            self._session.add(
                RelayNode(
                    relay_id=relay_id,
                    registered_by_id=registered_by_id,
                    room_slugs=room_slugs,
                    last_heartbeat_at=now,
                )
            )
        else:
            node.registered_by_id = registered_by_id
            node.room_slugs = room_slugs
            node.last_heartbeat_at = now
        await self._session.flush()

    async def heartbeat(self, relay_id: str, now: datetime) -> None:
        node = await self.get(relay_id)
        if node is not None:
            node.last_heartbeat_at = now
            await self._session.flush()
