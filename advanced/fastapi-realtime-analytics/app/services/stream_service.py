from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.analytics import EventStream
from app.repositories.stream_repository import StreamRepository
from app.schemas.analytics import StreamCreate, StreamRead, StreamStatus, StreamUpdate


class StreamService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._streams = StreamRepository(session)

    async def list_streams(self) -> list[StreamRead]:
        rows = await self._streams.list_all()
        return [StreamRead.model_validate(row) for row in rows]

    async def get_stream(self, key: str) -> StreamRead:
        row = await self._require_stream(key)
        return StreamRead.model_validate(row)

    async def create_stream(self, payload: StreamCreate) -> StreamRead:
        if await self._streams.get_by_key(payload.key) is not None:
            raise ConflictError("Another stream already uses this key")
        now = datetime.now(UTC)
        stream = EventStream(
            key=payload.key,
            name=payload.name,
            description=payload.description,
            status=StreamStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        await self._streams.add(stream)
        await self._session.commit()
        return StreamRead.model_validate(stream)

    async def update_stream(self, key: str, payload: StreamUpdate) -> StreamRead:
        stream = await self._require_stream(key)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            stream.name = changes["name"]
        if "description" in changes and changes["description"] is not None:
            stream.description = changes["description"]
        stream.updated_at = datetime.now(UTC)
        await self._streams.save()
        await self._session.commit()
        return StreamRead.model_validate(stream)

    async def pause_stream(self, key: str) -> StreamRead:
        stream = await self._require_stream(key)
        if stream.status == StreamStatus.PAUSED.value:
            raise ConflictError("Stream is already paused")
        stream.status = StreamStatus.PAUSED.value
        stream.updated_at = datetime.now(UTC)
        await self._streams.save()
        await self._session.commit()
        return StreamRead.model_validate(stream)

    async def resume_stream(self, key: str) -> StreamRead:
        stream = await self._require_stream(key)
        if stream.status == StreamStatus.ACTIVE.value:
            raise ConflictError("Stream is already active")
        stream.status = StreamStatus.ACTIVE.value
        stream.updated_at = datetime.now(UTC)
        await self._streams.save()
        await self._session.commit()
        return StreamRead.model_validate(stream)

    async def require_active_stream(self, key: str) -> EventStream:
        stream = await self._require_stream(key)
        if stream.status != StreamStatus.ACTIVE.value:
            raise ConflictError("Stream is paused; ingestion is disabled")
        return stream

    async def _require_stream(self, key: str) -> EventStream:
        stream = await self._streams.get_by_key(key)
        if stream is None:
            raise NotFoundError("Stream", key)
        return stream
