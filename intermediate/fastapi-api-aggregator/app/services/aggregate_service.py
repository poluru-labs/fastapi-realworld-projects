import asyncio

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.aggregator_repository import AggregateRecord, AggregatorRepository, RunRecord
from app.schemas.aggregate import (
    AggregateCreate,
    AggregateRead,
    AggregateRunRead,
    AggregateStatus,
    AggregateUpdate,
    FragmentResult,
    FragmentStep,
)
from app.schemas.user import UserRead, UserRole
from app.services.upstream_client import UpstreamClient


class AggregateService:
    def __init__(self, repository: AggregatorRepository, upstream: UpstreamClient) -> None:
        self._repo = repository
        self._upstream = upstream

    def list_aggregates(self, actor: UserRead) -> list[AggregateRead]:
        rows = self._repo.list_aggregates()
        if actor.role != UserRole.ADMIN:
            rows = [row for row in rows if row.owner_id == actor.id]
        rows.sort(key=lambda row: row.slug)
        return [self._read(row) for row in rows]

    def get_aggregate(self, slug: str, actor: UserRead) -> AggregateRead:
        record = self._require_visible_aggregate(slug, actor)
        return self._read(record)

    def create_aggregate(self, payload: AggregateCreate, actor: UserRead) -> AggregateRead:
        if self._repo.get_aggregate_by_slug(payload.slug):
            raise ConflictError(f"Aggregate slug {payload.slug!r} is already registered")
        self._validate_steps(payload.steps, actor)
        record = self._repo.create_aggregate(
            slug=payload.slug,
            title=payload.title,
            description=payload.description,
            steps=payload.steps,
            owner_id=actor.id,
        )
        return self._read(record)

    def update_aggregate(
        self,
        slug: str,
        payload: AggregateUpdate,
        actor: UserRead,
    ) -> AggregateRead:
        record = self._require_owned_aggregate(slug, actor)
        fields = payload.model_dump(exclude_unset=True)
        if "steps" in fields and fields["steps"] is not None:
            self._validate_steps(fields["steps"], actor)
        updated = self._repo.update_aggregate(record.id, **fields)
        assert updated is not None
        return self._read(updated)

    def publish_aggregate(self, slug: str, actor: UserRead) -> AggregateRead:
        record = self._require_owned_aggregate(slug, actor)
        if record.status == AggregateStatus.PUBLISHED:
            raise ConflictError("Aggregate is already published")
        updated = self._repo.update_aggregate(record.id, status=AggregateStatus.PUBLISHED)
        assert updated is not None
        return self._read(updated)

    def delete_aggregate(self, slug: str, actor: UserRead) -> None:
        record = self._require_owned_aggregate(slug, actor)
        if self._repo.delete_aggregate(record.id) is None:
            raise NotFoundError("Aggregate", slug)

    async def run_aggregate(
        self,
        slug: str,
        actor: UserRead,
        *,
        idempotency_key: str | None,
    ) -> AggregateRunRead:
        record = self._require_visible_aggregate(slug, actor)
        if record.status != AggregateStatus.PUBLISHED:
            raise ConflictError("Only published aggregates can be executed")
        if idempotency_key:
            cached = self._repo.find_run_by_idempotency(
                owner_id=actor.id,
                aggregate_slug=slug,
                idempotency_key=idempotency_key,
            )
            if cached is not None:
                return self._run_read(cached)

        fragments = await self._execute_steps(record.steps, actor)
        partial = any(fragment.status_code >= 400 for fragment in fragments)
        run = self._repo.save_run(
            aggregate_id=record.id,
            aggregate_slug=record.slug,
            owner_id=actor.id,
            partial=partial,
            fragments=[fragment.model_dump() for fragment in fragments],
            idempotency_key=idempotency_key,
        )
        return self._run_read(run)

    def list_runs(self, slug: str, actor: UserRead) -> list[AggregateRunRead]:
        record = self._require_visible_aggregate(slug, actor)
        runs = self._repo.list_runs_for_aggregate(record.id)
        runs.sort(key=lambda row: row.created_at, reverse=True)
        return [self._run_read(run) for run in runs]

    async def _execute_steps(
        self,
        steps: list[FragmentStep],
        actor: UserRead,
    ) -> list[FragmentResult]:
        tasks = [self._fetch_step(step, actor) for step in steps]
        return list(await asyncio.gather(*tasks))

    async def _fetch_step(self, step: FragmentStep, actor: UserRead) -> FragmentResult:
        source = self._repo.get_source_by_slug(step.source_slug)
        if source is None or (
            source.owner_id != actor.id and actor.role != UserRole.ADMIN
        ):
            return FragmentResult(
                key=step.key,
                source_slug=step.source_slug,
                status_code=404,
                error="Source not found for this caller",
            )
        if not source.is_active:
            return FragmentResult(
                key=step.key,
                source_slug=step.source_slug,
                status_code=409,
                error="Source is paused",
            )
        status_code, data, error = await self._upstream.fetch(
            catalog=source.mock_catalog,
            path=step.path,
            method=step.method,
        )
        return FragmentResult(
            key=step.key,
            source_slug=step.source_slug,
            status_code=status_code,
            data=data,
            error=error,
        )

    def _validate_steps(self, steps: list[FragmentStep], actor: UserRead) -> None:
        keys = {step.key for step in steps}
        if len(keys) != len(steps):
            raise ConflictError("Fragment keys must be unique within an aggregate")
        for step in steps:
            source = self._repo.get_source_by_slug(step.source_slug)
            if source is None or source.owner_id != actor.id:
                raise NotFoundError("Source", step.source_slug)

    def _require_visible_aggregate(self, slug: str, actor: UserRead) -> AggregateRecord:
        record = self._repo.get_aggregate_by_slug(slug)
        if record is None or (record.owner_id != actor.id and actor.role != UserRole.ADMIN):
            raise NotFoundError("Aggregate", slug)
        return record

    def _require_owned_aggregate(self, slug: str, actor: UserRead) -> AggregateRecord:
        record = self._repo.get_aggregate_by_slug(slug)
        if record is None or record.owner_id != actor.id:
            raise NotFoundError("Aggregate", slug)
        return record

    @staticmethod
    def _read(record: AggregateRecord) -> AggregateRead:
        return AggregateRead(
            id=record.id,
            slug=record.slug,
            title=record.title,
            description=record.description,
            status=record.status,
            steps=record.steps,
            owner_id=record.owner_id,
            run_path=f"/api/v1/aggregates/{record.slug}/runs",
            created_at=record.created_at,
        )

    @staticmethod
    def _run_read(record: RunRecord) -> AggregateRunRead:
        fragments = [FragmentResult.model_validate(item) for item in record.fragments]
        return AggregateRunRead(
            id=record.id,
            aggregate_slug=record.aggregate_slug,
            partial=record.partial,
            fragments=fragments,
            idempotency_key=record.idempotency_key,
            created_at=record.created_at,
        )
