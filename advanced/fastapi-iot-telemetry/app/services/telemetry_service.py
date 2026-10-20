import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.telemetry import TelemetryIdempotencyRecord, TelemetryReading
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.reading_repository import ReadingRepository
from app.schemas.telemetry import BatchIngestResult, ReadingBatchIngest, ReadingIngest, ReadingRead
from app.services.device_service import DeviceService


class TelemetryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._readings = ReadingRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._devices = DeviceService(session)

    async def ingest_one(
        self,
        device_key: str,
        ingest_token: str,
        payload: ReadingIngest,
        *,
        idempotency_key: str,
    ) -> ReadingRead:
        device = await self._devices.verify_ingest_token(device_key, ingest_token)
        cached = await self._load_idempotent(device.id, idempotency_key)
        if cached is not None:
            return cached
        reading = await self._persist(device.id, payload)
        await self._devices.touch_last_seen(device, reading.recorded_at)
        body = ReadingRead.model_validate(reading)
        await self._store_idempotent(device.id, idempotency_key, body)
        await self._session.commit()
        return body

    async def ingest_batch(
        self,
        device_key: str,
        ingest_token: str,
        payload: ReadingBatchIngest,
        *,
        idempotency_key: str,
    ) -> BatchIngestResult:
        device = await self._devices.verify_ingest_token(device_key, ingest_token)
        cached = await self._load_batch(device.id, idempotency_key)
        if cached is not None:
            return cached
        stored: list[ReadingRead] = []
        last_seen = device.last_seen_at
        for item in payload.readings:
            reading = await self._persist(device.id, item)
            stored.append(ReadingRead.model_validate(reading))
            if last_seen is None or reading.recorded_at > last_seen:
                last_seen = reading.recorded_at
        if last_seen is not None:
            await self._devices.touch_last_seen(device, last_seen)
        result = BatchIngestResult(accepted=len(stored), readings=stored)
        await self._store_batch_idempotent(device.id, idempotency_key, result)
        await self._session.commit()
        return result

    async def _persist(self, device_id: int, payload: ReadingIngest) -> TelemetryReading:
        if payload.dedupe_key is not None:
            if await self._readings.dedupe_exists(device_id, payload.dedupe_key):
                raise ConflictError("A reading with this dedupe_key already exists")
        now = datetime.now(UTC)
        recorded = payload.recorded_at if payload.recorded_at is not None else now
        if recorded.tzinfo is None:
            recorded = recorded.replace(tzinfo=UTC)
        reading = TelemetryReading(
            device_id=device_id,
            recorded_at=recorded,
            metrics=dict(payload.metrics),
            dedupe_key=payload.dedupe_key,
            ingested_at=now,
        )
        await self._readings.add(reading)
        return reading

    async def _load_idempotent(self, device_id: int, key: str) -> ReadingRead | None:
        record = await self._idempotency.get(device_id, key)
        if record is None:
            return None
        return ReadingRead.model_validate(json.loads(record.response_json))

    async def _load_batch(self, device_id: int, key: str) -> BatchIngestResult | None:
        record = await self._idempotency.get(device_id, key)
        if record is None:
            return None
        return BatchIngestResult.model_validate(json.loads(record.response_json))

    async def _store_idempotent(self, device_id: int, key: str, body: ReadingRead) -> None:
        await self._idempotency.add(
            TelemetryIdempotencyRecord(
                device_id=device_id,
                idempotency_key=key,
                response_json=body.model_dump_json(),
                status_code=201,
            )
        )

    async def _store_batch_idempotent(
        self,
        device_id: int,
        key: str,
        body: BatchIngestResult,
    ) -> None:
        await self._idempotency.add(
            TelemetryIdempotencyRecord(
                device_id=device_id,
                idempotency_key=key,
                response_json=body.model_dump_json(),
                status_code=201,
            )
        )
