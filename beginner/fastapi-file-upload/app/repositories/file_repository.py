from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class FileRecord:
    id: int
    filename: str
    content_type: str
    size_bytes: int
    description: str
    content: bytes
    uploaded_at: datetime = field(default_factory=_utcnow)


def _seed() -> dict[int, FileRecord]:
    return {
        1: FileRecord(
            id=1,
            filename="welcome.txt",
            content_type="text/plain",
            size_bytes=28,
            description="Sample text file from seed data.",
            content=b"Hello from the file upload API!",
            uploaded_at=datetime.fromisoformat("2026-02-01T10:00:00+00:00"),
        ),
        2: FileRecord(
            id=2,
            filename="notes.md",
            content_type="text/markdown",
            size_bytes=22,
            description="Markdown snippet.",
            content=b"# Demo\nUpload files.",
            uploaded_at=datetime.fromisoformat("2026-02-05T14:30:00+00:00"),
        ),
    }


class FileRepository:
    """In-memory uploaded files (content resets on restart)."""

    def __init__(self) -> None:
        self._files = _seed()
        self._next_id = max(self._files.keys(), default=0) + 1

    def list_files(self) -> list[FileRecord]:
        return list(self._files.values())

    def get_file(self, file_id: int) -> FileRecord | None:
        return self._files.get(file_id)

    def create_file(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        description: str,
    ) -> FileRecord:
        file_id = self._next_id
        self._next_id += 1
        record = FileRecord(
            id=file_id,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(content),
            description=description,
            content=content,
        )
        self._files[file_id] = record
        return record

    def update_description(self, file_id: int, description: str) -> FileRecord | None:
        record = self._files.get(file_id)
        if record is None:
            return None
        record.description = description
        return record

    def delete_file(self, file_id: int) -> FileRecord | None:
        return self._files.pop(file_id, None)


@lru_cache
def get_file_repository() -> FileRepository:
    return FileRepository()
