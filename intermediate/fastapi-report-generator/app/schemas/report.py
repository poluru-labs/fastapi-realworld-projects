from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportKind(StrEnum):
    SALES_SUMMARY = "sales_summary"
    ACTIVITY_LEDGER = "activity_ledger"


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class TemplateCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Q1 sales rollup",
                    "kind": "sales_summary",
                }
            ]
        },
    )

    name: str = Field(..., min_length=1, max_length=120)
    kind: ReportKind


class TemplateUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: ReportKind | None = None


class TemplateRead(BaseModel):
    id: int
    owner_id: int
    name: str
    kind: ReportKind
    created_at: datetime


class MetricRead(BaseModel):
    id: int
    category: str
    label: str
    amount: float
    occurred_at: datetime


class ReportGenerate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "template_id": 1,
                    "period_start": "2026-01-01T00:00:00+00:00",
                    "period_end": "2026-03-31T23:59:59+00:00",
                }
            ]
        },
    )

    template_id: int = Field(..., ge=1)
    period_start: datetime
    period_end: datetime

    @model_validator(mode="after")
    def period_valid(self) -> Self:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self


class ReportSection(BaseModel):
    title: str
    rows: list[dict[str, Any]]
    grand_total: float | None = None


class ReportResult(BaseModel):
    kind: ReportKind
    period_start: datetime
    period_end: datetime
    sections: list[ReportSection]
    row_count: int


class ReportRunRead(BaseModel):
    id: int
    owner_id: int
    template_id: int
    template_name: str
    status: RunStatus
    period_start: datetime
    period_end: datetime
    result: ReportResult | None
    created_at: datetime
    completed_at: datetime | None
