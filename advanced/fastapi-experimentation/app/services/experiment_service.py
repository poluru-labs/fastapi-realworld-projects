from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bucketing import pick_variant_key
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.experiment_tokens import (
    generate_experiment_token,
    hash_experiment_token,
    verify_experiment_token,
)
from app.models.experimentation import Experiment, ExperimentVariant
from app.repositories.experiment_repository import ExperimentRepository
from app.schemas.experimentation import (
    AssignmentRead,
    ExperimentCreate,
    ExperimentDetail,
    ExperimentProvisioned,
    ExperimentRead,
    ExperimentResults,
    ExperimentStatus,
    VariantCreate,
    VariantRead,
    VariantResults,
)


class ExperimentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ExperimentRepository(session)

    async def list_experiments(self) -> list[ExperimentRead]:
        rows = await self._repo.list_experiments()
        return [ExperimentRead.model_validate(row) for row in rows]

    async def provision(self, payload: ExperimentCreate) -> ExperimentProvisioned:
        if await self._repo.get_by_key(payload.key) is not None:
            raise ConflictError("Another experiment already uses this key")
        token = generate_experiment_token()
        now = datetime.now(UTC)
        row = Experiment(
            key=payload.key,
            name=payload.name,
            description=payload.description,
            status=ExperimentStatus.DRAFT.value,
            ingest_token_hash=hash_experiment_token(token),
            started_at=None,
            stopped_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._repo.add_experiment(row)
        await self._session.commit()
        body = ExperimentRead.model_validate(row)
        return ExperimentProvisioned(**body.model_dump(), ingest_token=token)

    async def get_detail(self, key: str) -> ExperimentDetail:
        experiment = await self._require_experiment(key)
        variants = await self._repo.list_variants(experiment.id)
        return ExperimentDetail(
            **ExperimentRead.model_validate(experiment).model_dump(),
            variants=[VariantRead.model_validate(v) for v in variants],
        )

    async def add_variant(self, key: str, payload: VariantCreate) -> VariantRead:
        experiment = await self._require_experiment(key)
        if experiment.status != ExperimentStatus.DRAFT.value:
            raise ConflictError("Variants can only be added while the experiment is a draft")
        if await self._repo.get_variant(experiment.id, payload.key) is not None:
            raise ConflictError("Variant key already exists on this experiment")
        row = ExperimentVariant(
            experiment_id=experiment.id,
            key=payload.key,
            name=payload.name,
            weight=payload.weight,
            created_at=datetime.now(UTC),
        )
        await self._repo.add_variant(row)
        await self._session.commit()
        return VariantRead.model_validate(row)

    async def start(self, key: str) -> ExperimentRead:
        experiment = await self._require_experiment(key)
        if experiment.status != ExperimentStatus.DRAFT.value:
            raise ConflictError("Only draft experiments can be started")
        variants = await self._repo.list_variants(experiment.id)
        if len(variants) < 2:
            raise ConflictError("Add at least two variants before starting")
        total_weight = sum(variant.weight for variant in variants)
        if total_weight != 100:
            raise ConflictError("Variant weights must sum to 100 before starting")
        now = datetime.now(UTC)
        experiment.status = ExperimentStatus.RUNNING.value
        experiment.started_at = now
        experiment.updated_at = now
        await self._repo.save()
        await self._session.commit()
        return ExperimentRead.model_validate(experiment)

    async def stop(self, key: str) -> ExperimentRead:
        experiment = await self._require_experiment(key)
        if experiment.status != ExperimentStatus.RUNNING.value:
            raise ConflictError("Only running experiments can be stopped")
        now = datetime.now(UTC)
        experiment.status = ExperimentStatus.STOPPED.value
        experiment.stopped_at = now
        experiment.updated_at = now
        await self._repo.save()
        await self._session.commit()
        return ExperimentRead.model_validate(experiment)

    async def assignment(self, key: str, subject_id: str) -> AssignmentRead:
        experiment = await self._require_experiment(key)
        if experiment.status != ExperimentStatus.RUNNING.value:
            raise NotFoundError("Experiment", key)
        variants = await self._repo.list_variants(experiment.id)
        picked = pick_variant_key(
            experiment_key=experiment.key,
            subject_id=subject_id,
            variants=[(v.key, v.weight) for v in variants],
        )
        variant = next(v for v in variants if v.key == picked)
        return AssignmentRead(
            experiment_key=experiment.key,
            subject_id=subject_id,
            variant_key=variant.key,
            variant_name=variant.name,
        )

    async def results(self, key: str, *, window_minutes: int) -> ExperimentResults:
        experiment = await self._require_experiment(key)
        since = datetime.now(UTC) - timedelta(minutes=window_minutes)
        variants = await self._repo.list_variants(experiment.id)
        stats: list[VariantResults] = []
        for variant in variants:
            exposures = await self._repo.count_events_since(
                experiment.id, since=since, event_type="exposure", variant_key=variant.key
            )
            conversions = await self._repo.count_events_since(
                experiment.id, since=since, event_type="conversion", variant_key=variant.key
            )
            rate = round(conversions / exposures, 4) if exposures else None
            stats.append(
                VariantResults(
                    variant_key=variant.key,
                    exposures=exposures,
                    conversions=conversions,
                    conversion_rate=rate,
                )
            )
        return ExperimentResults(
            experiment_key=key,
            window_minutes=window_minutes,
            variants=stats,
        )

    async def verify_ingest_token(self, key: str, token: str) -> Experiment:
        experiment = await self._require_experiment(key)
        if experiment.status != ExperimentStatus.RUNNING.value:
            raise ConflictError("Experiment is not accepting events")
        if not verify_experiment_token(token, experiment.ingest_token_hash):
            raise UnauthorizedError("Invalid experiment ingest token")
        return experiment

    async def _require_experiment(self, key: str) -> Experiment:
        experiment = await self._repo.get_by_key(key)
        if experiment is None:
            raise NotFoundError("Experiment", key)
        return experiment
