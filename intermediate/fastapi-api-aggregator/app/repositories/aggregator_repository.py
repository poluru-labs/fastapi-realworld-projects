from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.schemas.aggregate import AggregateStatus, FragmentStep
from app.schemas.source import MockCatalog


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class SourceRecord:
    id: int
    slug: str
    display_name: str
    base_url: str
    mock_catalog: MockCatalog
    description: str
    is_active: bool
    owner_id: int
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class AggregateRecord:
    id: int
    slug: str
    title: str
    description: str
    status: AggregateStatus
    steps: list[FragmentStep]
    owner_id: int
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class RunRecord:
    id: int
    aggregate_id: int
    aggregate_slug: str
    owner_id: int
    partial: bool
    fragments: list[dict]
    idempotency_key: str | None
    created_at: datetime = field(default_factory=_utcnow)


def _seed() -> tuple[dict[int, SourceRecord], dict[int, AggregateRecord]]:
    sources = {
        1: SourceRecord(
            id=1,
            slug="users-svc",
            display_name="Users service",
            base_url="https://mock.local/users",
            mock_catalog=MockCatalog.USERS,
            description="Profile and preferences mock.",
            is_active=True,
            owner_id=2,
            created_at=datetime.fromisoformat("2026-02-01T10:00:00+00:00"),
        ),
        2: SourceRecord(
            id=2,
            slug="orders-svc",
            display_name="Orders service",
            base_url="https://mock.local/orders",
            mock_catalog=MockCatalog.ORDERS,
            description="Recent orders mock.",
            is_active=True,
            owner_id=2,
            created_at=datetime.fromisoformat("2026-02-01T10:05:00+00:00"),
        ),
    }
    aggregates = {
        1: AggregateRecord(
            id=1,
            slug="customer-360",
            title="Customer 360 view",
            description="Profile plus recent orders for support dashboards.",
            status=AggregateStatus.PUBLISHED,
            steps=[
                FragmentStep(key="profile", source_slug="users-svc", path="/v1/profile"),
                FragmentStep(key="recent_orders", source_slug="orders-svc", path="/v1/recent"),
            ],
            owner_id=2,
            created_at=datetime.fromisoformat("2026-02-02T09:00:00+00:00"),
        ),
        2: AggregateRecord(
            id=2,
            slug="draft-dashboard",
            title="Work in progress",
            description="Not runnable until published.",
            status=AggregateStatus.DRAFT,
            steps=[
                FragmentStep(key="profile", source_slug="users-svc", path="/v1/profile"),
            ],
            owner_id=2,
            created_at=datetime.fromisoformat("2026-02-03T09:00:00+00:00"),
        ),
    }
    return sources, aggregates


class AggregatorRepository:
    def __init__(self) -> None:
        sources, aggregates = _seed()
        self._sources = sources
        self._aggregates = aggregates
        self._runs: dict[int, RunRecord] = {}
        self._idempotency: dict[tuple[int, str, str], int] = {}
        self._next_source_id = max(self._sources.keys(), default=0) + 1
        self._next_aggregate_id = max(self._aggregates.keys(), default=0) + 1
        self._next_run_id = 1

    def list_sources(self) -> list[SourceRecord]:
        return list(self._sources.values())

    def get_source_by_id(self, source_id: int) -> SourceRecord | None:
        return self._sources.get(source_id)

    def get_source_by_slug(self, slug: str) -> SourceRecord | None:
        for record in self._sources.values():
            if record.slug == slug:
                return record
        return None

    def create_source(
        self,
        *,
        slug: str,
        display_name: str,
        base_url: str,
        mock_catalog: MockCatalog,
        description: str,
        owner_id: int,
    ) -> SourceRecord:
        source_id = self._next_source_id
        self._next_source_id += 1
        record = SourceRecord(
            id=source_id,
            slug=slug,
            display_name=display_name,
            base_url=base_url,
            mock_catalog=mock_catalog,
            description=description,
            is_active=True,
            owner_id=owner_id,
        )
        self._sources[source_id] = record
        return record

    def update_source(self, source_id: int, **fields) -> SourceRecord | None:
        record = self._sources.get(source_id)
        if record is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(record, key, value)
        return record

    def delete_source(self, source_id: int) -> SourceRecord | None:
        return self._sources.pop(source_id, None)

    def list_aggregates(self) -> list[AggregateRecord]:
        return list(self._aggregates.values())

    def get_aggregate_by_id(self, aggregate_id: int) -> AggregateRecord | None:
        return self._aggregates.get(aggregate_id)

    def get_aggregate_by_slug(self, slug: str) -> AggregateRecord | None:
        for record in self._aggregates.values():
            if record.slug == slug:
                return record
        return None

    def create_aggregate(
        self,
        *,
        slug: str,
        title: str,
        description: str,
        steps: list[FragmentStep],
        owner_id: int,
        status: AggregateStatus = AggregateStatus.DRAFT,
    ) -> AggregateRecord:
        aggregate_id = self._next_aggregate_id
        self._next_aggregate_id += 1
        record = AggregateRecord(
            id=aggregate_id,
            slug=slug,
            title=title,
            description=description,
            status=status,
            steps=steps,
            owner_id=owner_id,
        )
        self._aggregates[aggregate_id] = record
        return record

    def update_aggregate(self, aggregate_id: int, **fields) -> AggregateRecord | None:
        record = self._aggregates.get(aggregate_id)
        if record is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(record, key, value)
        return record

    def delete_aggregate(self, aggregate_id: int) -> AggregateRecord | None:
        return self._aggregates.pop(aggregate_id, None)

    def save_run(
        self,
        *,
        aggregate_id: int,
        aggregate_slug: str,
        owner_id: int,
        partial: bool,
        fragments: list[dict],
        idempotency_key: str | None,
    ) -> RunRecord:
        run_id = self._next_run_id
        self._next_run_id += 1
        record = RunRecord(
            id=run_id,
            aggregate_id=aggregate_id,
            aggregate_slug=aggregate_slug,
            owner_id=owner_id,
            partial=partial,
            fragments=fragments,
            idempotency_key=idempotency_key,
        )
        self._runs[run_id] = record
        if idempotency_key:
            self._idempotency[(owner_id, aggregate_slug, idempotency_key)] = run_id
        return record

    def find_run_by_idempotency(
        self,
        *,
        owner_id: int,
        aggregate_slug: str,
        idempotency_key: str,
    ) -> RunRecord | None:
        run_id = self._idempotency.get((owner_id, aggregate_slug, idempotency_key))
        if run_id is None:
            return None
        return self._runs.get(run_id)

    def list_runs_for_aggregate(self, aggregate_id: int) -> list[RunRecord]:
        return [
            run
            for run in self._runs.values()
            if run.aggregate_id == aggregate_id
        ]


@lru_cache
def get_aggregator_repository() -> AggregatorRepository:
    return AggregatorRepository()
