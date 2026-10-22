from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experimentation import (
    Experiment,
    ExperimentEvent,
    ExperimentIdempotencyRecord,
    ExperimentVariant,
)


class ExperimentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_experiments(self) -> list[Experiment]:
        result = await self._session.scalars(select(Experiment).order_by(Experiment.key))
        return list(result)

    async def get_by_key(self, key: str) -> Experiment | None:
        return await self._session.scalar(select(Experiment).where(Experiment.key == key))

    async def get_by_id(self, experiment_id: int) -> Experiment | None:
        return await self._session.get(Experiment, experiment_id)

    async def add_experiment(self, experiment: Experiment) -> Experiment:
        self._session.add(experiment)
        await self._session.flush()
        return experiment

    async def save(self) -> None:
        await self._session.flush()

    async def list_variants(self, experiment_id: int) -> list[ExperimentVariant]:
        result = await self._session.scalars(
            select(ExperimentVariant)
            .where(ExperimentVariant.experiment_id == experiment_id)
            .order_by(ExperimentVariant.id)
        )
        return list(result)

    async def get_variant(self, experiment_id: int, variant_key: str) -> ExperimentVariant | None:
        return await self._session.scalar(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == experiment_id,
                ExperimentVariant.key == variant_key,
            )
        )

    async def add_variant(self, variant: ExperimentVariant) -> ExperimentVariant:
        self._session.add(variant)
        await self._session.flush()
        return variant

    async def add_event(self, event: ExperimentEvent) -> ExperimentEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def dedupe_exists(self, experiment_id: int, dedupe_key: str) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(ExperimentEvent)
            .where(
                ExperimentEvent.experiment_id == experiment_id,
                ExperimentEvent.dedupe_key == dedupe_key,
            )
        )
        return int(result or 0) > 0

    async def get_idempotency(
        self, experiment_id: int, key: str
    ) -> ExperimentIdempotencyRecord | None:
        return await self._session.scalar(
            select(ExperimentIdempotencyRecord).where(
                ExperimentIdempotencyRecord.experiment_id == experiment_id,
                ExperimentIdempotencyRecord.idempotency_key == key,
            )
        )

    async def add_idempotency(self, record: ExperimentIdempotencyRecord) -> None:
        self._session.add(record)
        await self._session.flush()

    async def count_events_since(
        self,
        experiment_id: int,
        *,
        since: datetime,
        event_type: str,
        variant_key: str,
    ) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(ExperimentEvent)
            .where(
                ExperimentEvent.experiment_id == experiment_id,
                ExperimentEvent.event_type == event_type,
                ExperimentEvent.variant_key == variant_key,
                ExperimentEvent.occurred_at >= since,
            )
        )
        return int(result or 0)
