from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import DbSession, IdempotencyKey, IngestKey
from app.schemas.analytics import (
    STREAM_KEY_PATTERN,
    BatchIngestResult,
    EventBatchIngest,
    EventIngest,
    EventRead,
)
from app.services.event_service import EventService

router = APIRouter()

StreamKey = Annotated[
    str,
    Path(pattern=STREAM_KEY_PATTERN.pattern, min_length=1, max_length=64),
]


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest one event",
    description=(
        "Requires **X-Ingest-Key** and **Idempotency-Key**. Retries with the same key "
        "return the stored event body. **dedupe_key** in the JSON prevents duplicate "
        "business ids within a stream."
    ),
    responses={
        409: {"description": "Stream paused, duplicate dedupe_key, or idempotency mismatch."},
        403: {"description": "Missing Idempotency-Key."},
    },
)
async def ingest_event(
    _: IngestKey,
    session: DbSession,
    stream_key: StreamKey,
    payload: EventIngest,
    idempotency_key: IdempotencyKey,
) -> EventRead:
    return await EventService(session).ingest_one(
        stream_key,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/batch",
    response_model=BatchIngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest up to 100 events",
    description=(
        "Same headers as single ingest. The entire batch is idempotent under one "
        "Idempotency-Key."
    ),
)
async def ingest_batch(
    _: IngestKey,
    session: DbSession,
    stream_key: StreamKey,
    payload: EventBatchIngest,
    idempotency_key: IdempotencyKey,
) -> BatchIngestResult:
    return await EventService(session).ingest_batch(
        stream_key,
        payload,
        idempotency_key=idempotency_key,
    )
