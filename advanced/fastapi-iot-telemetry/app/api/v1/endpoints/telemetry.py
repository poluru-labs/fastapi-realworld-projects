from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import DbSession, DeviceToken, IdempotencyKey
from app.schemas.telemetry import (
    DEVICE_KEY_PATTERN,
    BatchIngestResult,
    ReadingBatchIngest,
    ReadingIngest,
    ReadingRead,
)
from app.services.telemetry_service import TelemetryService

router = APIRouter()

DeviceKey = Annotated[
    str,
    Path(pattern=DEVICE_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.post(
    "",
    response_model=ReadingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest one reading",
    description=(
        "Requires **X-Device-Token** matching the provisioned device and **Idempotency-Key**. "
        "Use `recorded_at` for edge timestamps; late arrivals are stored as sent."
    ),
)
async def ingest_reading(
    device_key: DeviceKey,
    device_token: DeviceToken,
    session: DbSession,
    payload: ReadingIngest,
    idempotency_key: IdempotencyKey,
) -> ReadingRead:
    return await TelemetryService(session).ingest_one(
        device_key,
        device_token,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/batch",
    response_model=BatchIngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest up to 100 readings",
)
async def ingest_batch(
    device_key: DeviceKey,
    device_token: DeviceToken,
    session: DbSession,
    payload: ReadingBatchIngest,
    idempotency_key: IdempotencyKey,
) -> BatchIngestResult:
    return await TelemetryService(session).ingest_batch(
        device_key,
        device_token,
        payload,
        idempotency_key=idempotency_key,
    )
