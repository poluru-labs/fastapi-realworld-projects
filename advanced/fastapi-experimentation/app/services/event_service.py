import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bucketing import pick_variant_key
from app.core.exceptions import ConflictError
from app.models.experimentation import ExperimentEvent, ExperimentIdempotencyRecord
from app.repositories.experiment_repository import ExperimentRepository
from app.schemas.experimentation import EventIngest, EventRead
from app.services.experiment_service import ExperimentService


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ExperimentRepository(session)
        self._experiments = ExperimentService(session)

    async def ingest(
        self,
        experiment_key: str,
        token: str,
        idempotency_key: str,
        payload: EventIngest,
    ) -> EventRead:
        experiment = await self._experiments.verify_ingest_token(experiment_key, token)
        cached = await self._repo.get_idempotency(experiment.id, idempotency_key)
        if cached is not None:
            return EventRead.model_validate(json.loads(cached.response_json))

        dedupe = payload.dedupe_key or idempotency_key
        if await self._repo.dedupe_exists(experiment.id, dedupe):
            raise ConflictError("Duplicate event (dedupe_key)")

        variants = await self._repo.list_variants(experiment.id)
        if await self._repo.get_variant(experiment.id, payload.variant_key) is None:
            raise ConflictError("Unknown variant_key for this experiment")

        expected = pick_variant_key(
            experiment_key=experiment.key,
            subject_id=payload.subject_id,
            variants=[(v.key, v.weight) for v in variants],
        )
        if payload.variant_key != expected:
            raise ConflictError("variant_key does not match deterministic assignment")

        now = datetime.now(UTC)
        occurred = payload.occurred_at if payload.occurred_at is not None else now
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=UTC)

        event = ExperimentEvent(
            experiment_id=experiment.id,
            subject_id=payload.subject_id,
            event_type=payload.event_type.value,
            variant_key=payload.variant_key,
            occurred_at=occurred,
            properties=dict(payload.properties),
            dedupe_key=dedupe,
            ingested_at=now,
        )
        await self._repo.add_event(event)
        body = EventRead.model_validate(event)
        await self._repo.add_idempotency(
            ExperimentIdempotencyRecord(
                experiment_id=experiment.id,
                idempotency_key=idempotency_key,
                response_json=body.model_dump_json(),
                status_code=201,
            )
        )
        await self._session.commit()
        return body
