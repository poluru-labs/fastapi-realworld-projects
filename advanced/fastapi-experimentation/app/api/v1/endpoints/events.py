from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import DbSession, ExperimentToken, IdempotencyKey
from app.schemas.experimentation import EXPERIMENT_KEY_PATTERN, EventIngest, EventRead
from app.services.event_service import EventService

router = APIRouter()

ExperimentKey = Annotated[
    str,
    Path(pattern=EXPERIMENT_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest exposure or conversion",
    description=(
        "**X-Experiment-Token** and **Idempotency-Key** required. "
        "`variant_key` must match the deterministic assignment for `subject_id`."
    ),
)
async def ingest_event(
    session: DbSession,
    experiment_key: ExperimentKey,
    payload: EventIngest,
    ingest_token: ExperimentToken,
    idempotency_key: IdempotencyKey,
) -> EventRead:
    return await EventService(session).ingest(
        experiment_key,
        ingest_token,
        idempotency_key,
        payload,
    )
