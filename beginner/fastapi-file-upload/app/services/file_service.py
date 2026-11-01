from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError, PayloadTooLargeError
from app.repositories.file_repository import FileRepository
from app.schemas.file import FileRead, FileUpdate


class FileService:
    def __init__(self, repository: FileRepository, settings: Settings) -> None:
        self._repo = repository
        self._settings = settings

    def list_files(
        self,
        *,
        content_type: str | None,
        q: str | None,
    ) -> list[FileRead]:
        rows = self._repo.list_files()
        if content_type:
            needle = content_type.casefold()
            rows = [row for row in rows if needle in row.content_type.casefold()]
        if q:
            needle = q.casefold()
            rows = [
                row
                for row in rows
                if needle in row.filename.casefold() or needle in row.description.casefold()
            ]
        rows.sort(key=lambda row: row.uploaded_at, reverse=True)
        return [self._read(row) for row in rows]

    def get_file(self, file_id: int) -> FileRead:
        return self._read(self._require_file(file_id))

    def get_content(self, file_id: int) -> tuple[bytes, str, str]:
        record = self._require_file(file_id)
        return record.content, record.content_type, record.filename

    async def upload_file(
        self,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
        description: str,
    ) -> FileRead:
        if not filename.strip():
            raise AppError("filename is required")
        if len(content) == 0:
            raise AppError("file must not be empty")
        if len(content) > self._settings.max_upload_bytes:
            raise PayloadTooLargeError(
                f"Maximum upload size is {self._settings.max_upload_bytes} bytes"
            )
        safe_name = filename.split("/")[-1].split("\\")[-1]
        record = self._repo.create_file(
            filename=safe_name,
            content_type=content_type or "application/octet-stream",
            content=content,
            description=description,
        )
        return self._read(record)

    def update_file(self, file_id: int, payload: FileUpdate) -> FileRead:
        fields = payload.model_dump(exclude_unset=True)
        if "description" not in fields:
            return self.get_file(file_id)
        record = self._repo.update_description(file_id, fields["description"] or "")
        if record is None:
            raise NotFoundError("File", file_id)
        return self._read(record)

    def delete_file(self, file_id: int) -> None:
        if self._repo.delete_file(file_id) is None:
            raise NotFoundError("File", file_id)

    def _require_file(self, file_id: int):
        record = self._repo.get_file(file_id)
        if record is None:
            raise NotFoundError("File", file_id)
        return record

    @staticmethod
    def _read(record) -> FileRead:
        return FileRead(
            id=record.id,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            description=record.description,
            download_path=f"/api/v1/files/{record.id}/content",
            uploaded_at=record.uploaded_at,
        )
