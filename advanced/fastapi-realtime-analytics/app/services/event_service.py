import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.analytics import AnalyticsEvent, IngestIdempotencyRecord
from app.repositories.event_repository import EventRepository
from app.repositories.ingest_idempotency_repository import IngestIdempotencyRepository
from app.repositories.stream_repository import StreamRepository
from app.schemas.analytics import BatchIngestResult, EventBatchIngest, EventIngest, EventRead
from app.services.stream_service import StreamService


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._streams = StreamRepository(session)
        self._events = EventRepository(session)
        self._idempotency = IngestIdempotencyRepository(session)
        self._stream_service = StreamService(session)

    async def ingest_one(
        self,
        stream_key: str,
        payload: EventIngest,
        *,
        idempotency_key: str,
    ) -> EventRead:
        stream = await self._stream_service.require_active_stream(stream_key)
        cached = await self._load_idempotent(stream.id, idempotency_key)
        if cached is not None:
            return cached

        event = await self._persist_event(stream.id, payload)
        body = EventRead.model_validate(event)
        await self._store_idempotent(stream.id, idempotency_key, body)
        await self._session.commit()
        return body

    async def ingest_batch(
        self,
        stream_key: str,
        payload: EventBatchIngest,
        *,
        idempotency_key: str,
    ) -> BatchIngestResult:
        stream = await self._stream_service.require_active_stream(stream_key)
        cached = await self._load_batch_idempotent(stream.id, idempotency_key)
        if cached is not None:
            return cached

        stored: list[EventRead] = []
        for item in payload.events:
            event = await self._persist_event(stream.id, item)
            stored.append(EventRead.model_validate(event))

        result = BatchIngestResult(accepted=len(stored), events=stored)
        await self._store_batch_idempotent(stream.id, idempotency_key, result)
        await self._session.commit()
        return result

    async def _persist_event(self, stream_id: int, payload: EventIngest) -> AnalyticsEvent:
        now = datetime.now(UTC)
        occurred = payload.occurred_at if payload.occurred_at is not None else now
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=UTC)
        if payload.dedupe_key is not None:
            exists = await self._events.dedupe_exists(stream_id, payload.dedupe_key)
            if exists:
                raise ConflictError("An event with this dedupe_key already exists in the stream")
        event = AnalyticsEvent(
            stream_id=stream_id,
            event_name=payload.event_name,
            occurred_at=occurred,
            properties=dict(payload.properties),
            dedupe_key=payload.dedupe_key,
            ingested_at=now,
        )
        await self._events.add(event)
        return event

    async def _load_idempotent(self, stream_id: int, key: str) -> EventRead | None:
        record = await self._idempotency.get(stream_id, key)
        if record is None:
            return None
        data = json.loads(record.response_json)
        return EventRead.model_validate(data)

    async def _load_batch_idempotent(
        self,
        stream_id: int,
        key: str,
    ) -> BatchIngestResult | None:
        record = await self._idempotency.get(stream_id, key)
        if record is None:
            return None
        data = json.loads(record.response_json)
        return BatchIngestResult.model_validate(data)

    async def _store_idempotent(
        self,
        stream_id: int,
        key: str,
        body: EventRead,
    ) -> None:
        await self._idempotency.add(
            IngestIdempotencyRecord(
                stream_id=stream_id,
                idempotency_key=key,
                response_json=body.model_dump_json(),
                status_code=201,
            )
        )

    async def _store_batch_idempotent(
        self,
        stream_id: int,
        key: str,
        body: BatchIngestResult,
    ) -> None:
        await self._idempotency.add(
            IngestIdempotencyRecord(
                stream_id=stream_id,
                idempotency_key=key,
                response_json=body.model_dump_json(),
                status_code=201,
            )
        )
