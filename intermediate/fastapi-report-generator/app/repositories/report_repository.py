from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.schemas.report import ReportKind, RunStatus


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class TemplateRecord:
    id: int
    owner_id: int
    name: str
    kind: ReportKind
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class MetricRecord:
    id: int
    category: str
    label: str
    amount: float
    occurred_at: datetime


@dataclass
class RunRecord:
    id: int
    owner_id: int
    template_id: int
    period_start: datetime
    period_end: datetime
    status: RunStatus
    result_json: str | None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None


def _seed_metrics() -> dict[int, MetricRecord]:
    return {
        1: MetricRecord(
            id=1,
            category="saas",
            label="Acme renewal",
            amount=1200.0,
            occurred_at=datetime.fromisoformat("2026-01-15T10:00:00+00:00"),
        ),
        2: MetricRecord(
            id=2,
            category="saas",
            label="Beta signup",
            amount=400.0,
            occurred_at=datetime.fromisoformat("2026-02-02T14:00:00+00:00"),
        ),
        3: MetricRecord(
            id=3,
            category="services",
            label="Workshop day",
            amount=2500.0,
            occurred_at=datetime.fromisoformat("2026-02-20T09:00:00+00:00"),
        ),
        4: MetricRecord(
            id=4,
            category="hardware",
            label="Sensor kit",
            amount=890.5,
            occurred_at=datetime.fromisoformat("2026-03-05T16:30:00+00:00"),
        ),
        5: MetricRecord(
            id=5,
            category="services",
            label="Support block",
            amount=600.0,
            occurred_at=datetime.fromisoformat("2026-03-18T11:00:00+00:00"),
        ),
    }


class ReportRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._templates: dict[int, TemplateRecord] = {
            1: TemplateRecord(
                id=1,
                owner_id=1,
                name="Admin sales summary",
                kind=ReportKind.SALES_SUMMARY,
                created_at=now,
            ),
        }
        self._metrics = _seed_metrics()
        self._runs: dict[int, RunRecord] = {}
        self._next_template_id = 2
        self._next_run_id = 1

    def list_templates_for_owner(self, owner_id: int) -> list[TemplateRecord]:
        return [row for row in self._templates.values() if row.owner_id == owner_id]

    def list_all_templates(self) -> list[TemplateRecord]:
        return list(self._templates.values())

    def get_template(self, template_id: int) -> TemplateRecord | None:
        return self._templates.get(template_id)

    def add_template(self, record: TemplateRecord) -> TemplateRecord:
        self._templates[record.id] = record
        return record

    def allocate_template_id(self) -> int:
        template_id = self._next_template_id
        self._next_template_id += 1
        return template_id

    def update_template(
        self,
        template_id: int,
        *,
        name: str | None,
        kind: ReportKind | None,
    ) -> TemplateRecord | None:
        record = self._templates.get(template_id)
        if record is None:
            return None
        if name is not None:
            record.name = name
        if kind is not None:
            record.kind = kind
        return record

    def delete_template(self, template_id: int) -> TemplateRecord | None:
        return self._templates.pop(template_id, None)

    def list_metrics_between(self, start: datetime, end: datetime) -> list[MetricRecord]:
        rows = [
            metric
            for metric in self._metrics.values()
            if start <= metric.occurred_at <= end
        ]
        rows.sort(key=lambda metric: metric.occurred_at)
        return rows

    def list_metrics(self) -> list[MetricRecord]:
        rows = list(self._metrics.values())
        rows.sort(key=lambda metric: metric.occurred_at)
        return rows

    def list_runs_for_owner(self, owner_id: int) -> list[RunRecord]:
        rows = [run for run in self._runs.values() if run.owner_id == owner_id]
        rows.sort(key=lambda run: run.created_at, reverse=True)
        return rows

    def get_run(self, run_id: int) -> RunRecord | None:
        return self._runs.get(run_id)

    def add_run(self, record: RunRecord) -> RunRecord:
        self._runs[record.id] = record
        return record

    def allocate_run_id(self) -> int:
        run_id = self._next_run_id
        self._next_run_id += 1
        return run_id


@lru_cache
def get_report_repository() -> ReportRepository:
    return ReportRepository()
