"""Parse uploaded CSV files and create blog posts row by row.

The route only handles `UploadFile` and query flags. Parsing, validation, and
per-row error collection live here so you can test imports without HTTP.
"""

import csv
import io
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.repositories.import_job_repository import ImportJobRecord, ImportJobRepository
from app.schemas.import_job import (
    CSV_TEMPLATE_TEXT,
    OPTIONAL_CSV_COLUMNS,
    REQUIRED_CSV_COLUMNS,
    CsvPostRow,
    ImportJobPage,
    ImportJobRead,
    ImportJobStatus,
    ImportRowError,
)
from app.schemas.user import UserRead
from app.services.post_service import PostService


class CsvImportService:
    def __init__(
        self,
        *,
        settings: Settings,
        jobs: ImportJobRepository,
        posts: PostService,
    ) -> None:
        self._settings = settings
        self._jobs = jobs
        self._posts = posts

    def template_csv(self) -> str:
        return CSV_TEMPLATE_TEXT

    def get_job(self, actor: UserRead, job_id: str) -> ImportJobRead:
        record = self._jobs.get(job_id)
        if record is None or record.author_id != actor.id:
            raise NotFoundError("Import job", job_id)
        return record.to_read()

    def list_jobs(self, actor: UserRead, *, limit: int, offset: int) -> ImportJobPage:
        rows = self._jobs.list_for_author(actor.id)
        page = rows[offset : offset + limit]
        return ImportJobPage(
            items=[job.to_read() for job in page],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def import_posts(
        self,
        actor: UserRead,
        *,
        filename: str,
        content: bytes,
        dry_run: bool,
    ) -> ImportJobRead:
        if not filename.lower().endswith(".csv"):
            raise BadRequestError("Upload a file whose name ends with .csv")
        if not content.strip():
            raise BadRequestError("The uploaded file is empty")
        if len(content) > self._settings.csv_max_upload_bytes:
            raise BadRequestError(
                f"File exceeds the {self._settings.csv_max_upload_bytes} byte upload limit"
            )

        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise BadRequestError("CSV must include a header row")

        normalized_headers = {name.strip().casefold() for name in reader.fieldnames if name}
        missing = [col for col in REQUIRED_CSV_COLUMNS if col not in normalized_headers]
        if missing:
            raise BadRequestError(
                f"Missing required column(s): {', '.join(missing)}. "
                f"Expected header includes at least: {', '.join(REQUIRED_CSV_COLUMNS)}. "
                f"Optional: {', '.join(OPTIONAL_CSV_COLUMNS)}."
            )

        # Map actual header spelling to canonical keys (case-insensitive).
        header_map = {
            (name.strip().casefold()): name.strip()
            for name in reader.fieldnames
            if name and name.strip()
        }

        errors: list[ImportRowError] = []
        created_slugs: list[str] = []
        created_count = 0
        published_count = 0
        skipped_count = 0
        total_rows = 0

        for row_number, raw_row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            total_rows += 1
            if total_rows > self._settings.csv_max_rows:
                errors.append(
                    ImportRowError(
                        row_number=row_number,
                        field=None,
                        message=(
                            f"Stopped at row limit ({self._settings.csv_max_rows}). "
                            "Split the file or raise CSV_MAX_ROWS."
                        ),
                    )
                )
                skipped_count += 1
                break

            record = {
                canonical: raw_row.get(header_map.get(canonical, canonical), "") or ""
                for canonical in REQUIRED_CSV_COLUMNS + OPTIONAL_CSV_COLUMNS
            }

            try:
                parsed = CsvPostRow.from_csv_record(record, row_number=row_number)
            except ValueError as exc:
                errors.append(
                    ImportRowError(row_number=row_number, field=None, message=str(exc))
                )
                skipped_count += 1
                continue

            if dry_run:
                continue

            try:
                created = self._posts.create_post(actor, parsed.to_post_create())
            except ConflictError as exc:
                errors.append(
                    ImportRowError(row_number=row_number, field="slug", message=exc.message)
                )
                skipped_count += 1
                continue

            created_count += 1
            created_slugs.append(created.slug)

            if parsed.publish:
                try:
                    self._posts.publish(actor, created.slug)
                    published_count += 1
                except ConflictError as exc:
                    errors.append(
                        ImportRowError(
                            row_number=row_number,
                            field="publish",
                            message=exc.message,
                        )
                    )

        job = ImportJobRecord(
            id=str(uuid4()),
            filename=filename,
            dry_run=dry_run,
            status=ImportJobStatus.COMPLETED,
            total_rows=total_rows,
            created_count=created_count,
            published_count=published_count,
            skipped_count=skipped_count,
            errors=errors,
            created_slugs=created_slugs,
            author_id=actor.id,
            created_at=datetime.now(UTC),
        )
        self._jobs.add(job)
        return job.to_read()
