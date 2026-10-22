from collections import defaultdict
from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError, NotFoundError
from app.repositories.report_repository import ReportRepository, RunRecord, TemplateRecord
from app.schemas.report import (
    MetricRead,
    ReportGenerate,
    ReportKind,
    ReportResult,
    ReportRunRead,
    ReportSection,
    RunStatus,
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
)
from app.schemas.user import UserRead, UserRole


class ReportService:
    def __init__(self, repository: ReportRepository) -> None:
        self._repo = repository

    def list_templates(self, current_user: UserRead) -> list[TemplateRead]:
        if current_user.role is UserRole.ADMIN:
            rows = self._repo.list_all_templates()
        else:
            rows = self._repo.list_templates_for_owner(current_user.id)
        rows.sort(key=lambda row: (row.name.casefold(), row.id))
        return [self._template_read(row) for row in rows]

    def create_template(self, current_user: UserRead, payload: TemplateCreate) -> TemplateRead:
        record = TemplateRecord(
            id=self._repo.allocate_template_id(),
            owner_id=current_user.id,
            name=payload.name,
            kind=payload.kind,
            created_at=datetime.now(UTC),
        )
        self._repo.add_template(record)
        return self._template_read(record)

    def get_template(self, current_user: UserRead, template_id: int) -> TemplateRead:
        return self._template_read(self._require_template_access(current_user, template_id))

    def update_template(
        self,
        current_user: UserRead,
        template_id: int,
        payload: TemplateUpdate,
    ) -> TemplateRead:
        self._require_template_owner(current_user, template_id)
        fields = payload.model_dump(exclude_unset=True)
        record = self._repo.update_template(
            template_id,
            name=fields.get("name"),
            kind=fields.get("kind"),
        )
        if record is None:
            raise NotFoundError("Template", template_id)
        return self._template_read(record)

    def delete_template(self, current_user: UserRead, template_id: int) -> None:
        self._require_template_owner(current_user, template_id)
        if self._repo.delete_template(template_id) is None:
            raise NotFoundError("Template", template_id)

    def list_metrics(self, current_user: UserRead) -> list[MetricRead]:
        if current_user.role is not UserRole.ADMIN:
            raise ForbiddenError("Metrics catalog requires admin role")
        return [
            MetricRead(
                id=row.id,
                category=row.category,
                label=row.label,
                amount=row.amount,
                occurred_at=row.occurred_at,
            )
            for row in self._repo.list_metrics()
        ]

    def list_runs(self, current_user: UserRead) -> list[ReportRunRead]:
        rows = self._repo.list_runs_for_owner(current_user.id)
        return [self._run_read(row) for row in rows]

    def generate(self, current_user: UserRead, payload: ReportGenerate) -> ReportRunRead:
        template = self._require_template_access(current_user, payload.template_id)
        period_start = self._aware(payload.period_start)
        period_end = self._aware(payload.period_end)
        run = RunRecord(
            id=self._repo.allocate_run_id(),
            owner_id=current_user.id,
            template_id=template.id,
            period_start=period_start,
            period_end=period_end,
            status=RunStatus.COMPLETED,
            result_json=None,
            created_at=datetime.now(UTC),
            completed_at=None,
        )
        metrics = self._repo.list_metrics_between(period_start, period_end)
        result = self._build_result(template.kind, metrics, period_start, period_end)
        run.result_json = result.model_dump_json()
        run.completed_at = datetime.now(UTC)
        self._repo.add_run(run)
        return self._run_read(run)

    def get_run(self, current_user: UserRead, run_id: int) -> ReportRunRead:
        run = self._require_run_owner(current_user, run_id)
        return self._run_read(run)

    def _build_result(
        self,
        kind: ReportKind,
        metrics,
        period_start: datetime,
        period_end: datetime,
    ) -> ReportResult:
        if kind is ReportKind.SALES_SUMMARY:
            totals: dict[str, float] = defaultdict(float)
            for metric in metrics:
                totals[metric.category] += metric.amount
            rows = [
                {"category": category, "total": round(total, 2)}
                for category, total in sorted(totals.items())
            ]
            grand = round(sum(totals.values()), 2)
            sections = [
                ReportSection(title="Totals by category", rows=rows, grand_total=grand),
            ]
        else:
            rows = [
                {
                    "occurred_at": metric.occurred_at.isoformat(),
                    "category": metric.category,
                    "label": metric.label,
                    "amount": metric.amount,
                }
                for metric in metrics
            ]
            sections = [ReportSection(title="Activity ledger", rows=rows, grand_total=None)]
        return ReportResult(
            kind=kind,
            period_start=period_start,
            period_end=period_end,
            sections=sections,
            row_count=len(metrics),
        )

    def _require_template_access(self, current_user: UserRead, template_id: int) -> TemplateRecord:
        record = self._repo.get_template(template_id)
        if record is None:
            raise NotFoundError("Template", template_id)
        if current_user.role is not UserRole.ADMIN and record.owner_id != current_user.id:
            raise NotFoundError("Template", template_id)
        return record

    def _require_template_owner(self, current_user: UserRead, template_id: int) -> TemplateRecord:
        record = self._require_template_access(current_user, template_id)
        if record.owner_id != current_user.id:
            raise NotFoundError("Template", template_id)
        return record

    def _require_run_owner(self, current_user: UserRead, run_id: int) -> RunRecord:
        run = self._repo.get_run(run_id)
        if run is None or run.owner_id != current_user.id:
            raise NotFoundError("Report run", run_id)
        return run

    @staticmethod
    def _template_read(record: TemplateRecord) -> TemplateRead:
        return TemplateRead(
            id=record.id,
            owner_id=record.owner_id,
            name=record.name,
            kind=record.kind,
            created_at=record.created_at,
        )

    def _run_read(self, run: RunRecord) -> ReportRunRead:
        template = self._repo.get_template(run.template_id)
        template_name = template.name if template is not None else "Unknown"
        result: ReportResult | None = None
        if run.result_json and run.status is RunStatus.COMPLETED:
            result = ReportResult.model_validate_json(run.result_json)
        return ReportRunRead(
            id=run.id,
            owner_id=run.owner_id,
            template_id=run.template_id,
            template_name=template_name,
            status=run.status,
            period_start=run.period_start,
            period_end=run.period_end,
            result=result,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )

    @staticmethod
    def _aware(when: datetime) -> datetime:
        if when.tzinfo is None:
            return when.replace(tzinfo=UTC)
        return when
