from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.library_repository import FolderRecord, LibraryRepository
from app.schemas.document import slugify
from app.schemas.folder import FolderCreate, FolderRead, FolderUpdate
from app.schemas.user import UserRead, UserRole


class FolderService:
    def __init__(self, repository: LibraryRepository) -> None:
        self._repo = repository

    def list_folders(self, actor: UserRead) -> list[FolderRead]:
        rows = self._repo.list_folders()
        if actor.role is not UserRole.ADMIN:
            rows = [folder for folder in rows if folder.owner_id == actor.id]
        rows.sort(key=lambda folder: folder.name.casefold())
        return [self._read(folder) for folder in rows]

    def get_folder(self, actor: UserRead | None, folder_slug: str) -> FolderRead:
        return self._read(self._visible_folder(actor, folder_slug))

    def create_folder(self, actor: UserRead, payload: FolderCreate) -> FolderRead:
        slug = payload.slug or slugify(payload.name)
        if not slug:
            raise ConflictError("Could not derive a folder slug from the name")
        if self._repo.folder_slug_taken(slug):
            raise ConflictError("Another folder already uses this slug")
        now = datetime.now(UTC)
        record = FolderRecord(
            id=self._repo.allocate_folder_id(),
            slug=slug,
            name=payload.name,
            description=payload.description,
            owner_id=actor.id,
            created_at=now,
        )
        self._repo.add_folder(record)
        return self._read(record)

    def update_folder(
        self,
        actor: UserRead,
        folder_slug: str,
        payload: FolderUpdate,
    ) -> FolderRead:
        record = self._owned_folder(actor, folder_slug)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            record.name = changes["name"]
        if "description" in changes:
            record.description = changes["description"] or ""
        self._repo.save_folder(record)
        return self._read(record)

    def delete_folder(self, actor: UserRead, folder_slug: str) -> None:
        record = self._owned_folder(actor, folder_slug)
        self._repo.delete_folder(record.id)

    def visible_folder_record(self, actor: UserRead | None, folder_slug: str) -> FolderRecord:
        return self._visible_folder(actor, folder_slug)

    def _visible_folder(self, actor: UserRead | None, folder_slug: str) -> FolderRecord:
        record = self._repo.get_folder_by_slug(folder_slug)
        if record is None:
            raise NotFoundError("Folder", folder_slug)
        if actor is not None and (
            actor.role is UserRole.ADMIN or actor.id == record.owner_id
        ):
            return record
        has_published = any(
            doc.status.value == "published"
            for doc in self._repo.list_documents_in_folder(record.id)
        )
        if not has_published:
            raise NotFoundError("Folder", folder_slug)
        return record

    def _owned_folder(self, actor: UserRead, folder_slug: str) -> FolderRecord:
        record = self._repo.get_folder_by_slug(folder_slug)
        if record is None or record.owner_id != actor.id:
            raise NotFoundError("Folder", folder_slug)
        return record

    def _read(self, record: FolderRecord) -> FolderRead:
        doc_count = len(self._repo.list_documents_in_folder(record.id))
        return FolderRead(
            id=record.id,
            slug=record.slug,
            name=record.name,
            description=record.description,
            owner_id=record.owner_id,
            document_count=doc_count,
            created_at=record.created_at,
        )
