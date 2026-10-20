from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import EventStream


class StreamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[EventStream]:
        result = await self._session.scalars(select(EventStream).order_by(EventStream.key))
        return list(result)

    async def get_by_key(self, key: str) -> EventStream | None:
        return await self._session.scalar(select(EventStream).where(EventStream.key == key))

    async def get_by_id(self, stream_id: int) -> EventStream | None:
        return await self._session.get(EventStream, stream_id)

    async def add(self, stream: EventStream) -> EventStream:
        self._session.add(stream)
        await self._session.flush()
        return stream

    async def save(self) -> None:
        await self._session.flush()
