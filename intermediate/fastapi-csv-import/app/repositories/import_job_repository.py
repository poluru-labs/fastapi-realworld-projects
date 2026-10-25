from dataclasses import dataclass
from datetime import datetime

from app.schemas.import_job import ImportJobRead, ImportJobStatus, ImportRowError


@dataclass
class ImportJobRecord:
    id: str
    filename: str
    dry_run: bool
    status: ImportJobStatus
    total_rows: int
    created_count: int
    published_count: int
    skipped_count: int
    errors: list[ImportRowError]
    created_slugs: list[str]
    author_id: int
    created_at: datetime

    def to_read(self) -> ImportJobRead:
        return ImportJobRead(
            id=self.id,
            filename=self.filename,
            dry_run=self.dry_run,
            status=self.status,
            total_rows=self.total_rows,
            created_count=self.created_count,
            published_count=self.published_count,
            skipped_count=self.skipped_count,
            errors=list(self.errors),
            created_slugs=list(self.created_slugs),
            author_id=self.author_id,
            created_at=self.created_at,
        )


class ImportJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, ImportJobRecord] = {}

    def add(self, record: ImportJobRecord) -> ImportJobRecord:
        self._jobs[record.id] = record
        return record

    def get(self, job_id: str) -> ImportJobRecord | None:
        return self._jobs.get(job_id)

    def list_for_author(self, author_id: int) -> list[ImportJobRecord]:
        rows = [job for job in self._jobs.values() if job.author_id == author_id]
        rows.sort(key=lambda job: job.created_at, reverse=True)
        return rows
