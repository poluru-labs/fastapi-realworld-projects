from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.post import PostCreate, normalize_tags

REQUIRED_CSV_COLUMNS = ("title", "body")
OPTIONAL_CSV_COLUMNS = ("summary", "tags", "slug", "publish")
CSV_TEMPLATE_COLUMNS = REQUIRED_CSV_COLUMNS + OPTIONAL_CSV_COLUMNS

CSV_TEMPLATE_TEXT = """title,summary,body,tags,slug,publish
My first import,Short blurb,Full post body here.,fastapi|csv,,false
Launch notes,,We shipped CSV import.,docs,,true
"""


class ImportJobStatus(StrEnum):
    COMPLETED = "completed"


class ImportRowError(BaseModel):
    """One row that failed validation or business rules."""

    row_number: int = Field(..., ge=2, description="1-based line number in the uploaded file")
    field: str | None = Field(None, description="Column name when the failure maps to one field")
    message: str = Field(..., description="Human-readable reason the row was skipped")


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    dry_run: bool = Field(
        ...,
        description="When true, the file was parsed and validated but no posts were written.",
    )
    status: ImportJobStatus
    total_rows: int = Field(
        ...,
        ge=0,
        description="Data rows read after the header (blank lines skipped)",
    )
    created_count: int = Field(
        ...,
        ge=0,
        description="Draft posts created (0 when dry_run is true)",
    )
    published_count: int = Field(
        ...,
        ge=0,
        description="Rows that were published after create (0 when dry_run is true)",
    )
    skipped_count: int = Field(..., ge=0, description="Rows with errors; see `errors`")
    errors: list[ImportRowError] = Field(default_factory=list)
    created_slugs: list[str] = Field(
        default_factory=list,
        description="Slugs assigned on this run (empty when dry_run is true)",
    )
    author_id: int
    created_at: datetime


class ImportJobPage(BaseModel):
    items: list[ImportJobRead]
    total: int
    limit: int
    offset: int


class CsvPostRow(BaseModel):
    """One CSV data row after column names are mapped."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    summary: str = Field(default="", max_length=280)
    body: str = Field(..., min_length=1, max_length=20_000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    slug: str | None = Field(default=None, max_length=80)
    publish: bool = False

    @classmethod
    def from_csv_record(cls, record: dict[str, str | None], *, row_number: int) -> Self:
        def cell(name: str) -> str:
            raw = record.get(name)
            return raw.strip() if raw else ""

        tags_raw = cell("tags")
        tags = [part.strip() for part in tags_raw.split("|") if part.strip()] if tags_raw else []
        publish_raw = cell("publish").casefold()
        publish = publish_raw in {"true", "1", "yes", "y"}

        try:
            normalized_tags = normalize_tags(tags)
        except ValueError as exc:
            raise ValueError(f"Row {row_number}: tags — {exc}") from exc

        payload = {
            "title": cell("title"),
            "summary": cell("summary"),
            "body": cell("body"),
            "tags": normalized_tags,
            "slug": cell("slug") or None,
            "publish": publish,
        }
        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = first.get("loc", ())
            field = str(loc[0]) if loc else None
            message = first.get("msg", "Invalid row")
            raise ValueError(f"Row {row_number}: {field or 'row'} — {message}") from exc

    def to_post_create(self) -> PostCreate:
        return PostCreate(
            title=self.title,
            summary=self.summary,
            body=self.body,
            tags=self.tags,
            slug=self.slug,
        )
