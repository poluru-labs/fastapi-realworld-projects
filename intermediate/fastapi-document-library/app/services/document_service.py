from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.library_repository import DocumentRecord, LibraryRepository, RevisionRecord
from app.repositories.user_repository import UserRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentPage,
    DocumentRead,
    DocumentStatus,
    DocumentUpdate,
    RevisionRead,
    TagCount,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.DRAFT: {DocumentStatus.PUBLISHED},
    DocumentStatus.PUBLISHED: {DocumentStatus.DRAFT, DocumentStatus.ARCHIVED},
    DocumentStatus.ARCHIVED: {DocumentStatus.DRAFT},
}


def _can_view(actor: UserRead | None, record: DocumentRecord) -> bool:
    if record.status is DocumentStatus.PUBLISHED:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.author_id


class DocumentService:
    def __init__(self, repository: LibraryRepository, users: UserRepository) -> None:
        self._repo = repository
        self._users = users

    def list_in_folder(
        self,
        actor: UserRead | None,
        folder_slug: str,
        *,
        status: DocumentStatus | None,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        folder = self._repo.get_folder_by_slug(folder_slug)
        if folder is None:
            raise NotFoundError("Folder", folder_slug)
        rows = self._repo.list_documents_in_folder(folder.id)
        visible = [doc for doc in rows if _can_view(actor, doc)]
        if status is not None:
            visible = [doc for doc in visible if doc.status is status]
        visible.sort(key=lambda doc: (doc.updated_at, doc.id), reverse=True)
        return self._page(folder.slug, visible, limit=limit, offset=offset)

    def list_published_library(
        self,
        *,
        tag: str | None,
        folder_slug: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        rows = [
            doc
            for doc in self._repo.list_documents()
            if doc.status is DocumentStatus.PUBLISHED
            and self._matches(doc, tag, folder_slug, query)
        ]
        rows.sort(key=lambda doc: (doc.published_at or doc.created_at, doc.id), reverse=True)
        return self._page_global(rows, limit=limit, offset=offset)

    def get_document(
        self,
        actor: UserRead | None,
        folder_slug: str,
        doc_slug: str,
    ) -> DocumentRead:
        record = self._visible_record(actor, folder_slug, doc_slug)
        folder = self._repo.get_folder(record.folder_id)
        assert folder is not None
        return self._to_read(folder.slug, record)

    def create_document(
        self,
        actor: UserRead,
        folder_slug: str,
        payload: DocumentCreate,
    ) -> DocumentRead:
        folder = self._owned_folder(actor, folder_slug)
        slug = payload.slug or slugify(payload.title)
        if not slug:
            raise ConflictError("Could not derive a document slug from the title")
        if self._repo.document_slug_taken(folder.id, slug):
            raise ConflictError("Another document in this folder already uses this slug")
        now = datetime.now(UTC)
        record = DocumentRecord(
            id=self._repo.allocate_document_id(),
            folder_id=folder.id,
            author_id=actor.id,
            slug=slug,
            title=payload.title,
            summary=payload.summary,
            body=payload.body,
            status=DocumentStatus.DRAFT,
            tags=list(payload.tags),
            version=0,
            created_at=now,
            updated_at=now,
            published_at=None,
        )
        self._repo.add_document(record)
        return self._to_read(folder.slug, record)

    def update_document(
        self,
        actor: UserRead,
        folder_slug: str,
        doc_slug: str,
        payload: DocumentUpdate,
    ) -> DocumentRead:
        folder = self._repo.get_folder_by_slug(folder_slug)
        if folder is None:
            raise NotFoundError("Folder", folder_slug)
        record = self._visible_record(actor, folder_slug, doc_slug)
        self._require_author(actor, record)
        changes = payload.model_dump(exclude_unset=True)
        if "title" in changes:
            record.title = changes["title"]
        if "summary" in changes:
            record.summary = changes["summary"] or ""
        if "body" in changes:
            record.body = changes["body"]
        if "tags" in changes:
            record.tags = list(changes["tags"])
        record.updated_at = datetime.now(UTC)
        self._repo.save_document(record)
        return self._to_read(folder.slug, record)

    def publish(self, actor: UserRead, folder_slug: str, doc_slug: str) -> DocumentRead:
        folder = self._repo.get_folder_by_slug(folder_slug)
        assert folder is not None
        record = self._visible_record(actor, folder_slug, doc_slug)
        self._require_author(actor, record)
        self._move(
            record,
            source=DocumentStatus.DRAFT,
            target=DocumentStatus.PUBLISHED,
            message="Only a draft can be published",
        )
        now = datetime.now(UTC)
        record.version += 1
        record.published_at = now
        record.updated_at = now
        self._repo.add_revision(
            RevisionRecord(
                document_id=record.id,
                version=record.version,
                title=record.title,
                body=record.body,
                published_at=now,
            )
        )
        self._repo.save_document(record)
        return self._to_read(folder.slug, record)

    def unpublish(self, actor: UserRead, folder_slug: str, doc_slug: str) -> DocumentRead:
        folder = self._repo.get_folder_by_slug(folder_slug)
        assert folder is not None
        record = self._visible_record(actor, folder_slug, doc_slug)
        self._require_author(actor, record)
        self._move(
            record,
            source=DocumentStatus.PUBLISHED,
            target=DocumentStatus.DRAFT,
            message="Only a published document can be unpublished",
        )
        record.published_at = None
        record.updated_at = datetime.now(UTC)
        self._repo.save_document(record)
        return self._to_read(folder.slug, record)

    def archive(self, actor: UserRead, folder_slug: str, doc_slug: str) -> DocumentRead:
        folder = self._repo.get_folder_by_slug(folder_slug)
        assert folder is not None
        record = self._visible_record(actor, folder_slug, doc_slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.author_id:
            raise ForbiddenError("Only the author or an admin can archive this document")
        self._move(
            record,
            source=DocumentStatus.PUBLISHED,
            target=DocumentStatus.ARCHIVED,
            message="Only a published document can be archived",
        )
        record.updated_at = datetime.now(UTC)
        self._repo.save_document(record)
        return self._to_read(folder.slug, record)

    def restore(self, actor: UserRead, folder_slug: str, doc_slug: str) -> DocumentRead:
        folder = self._repo.get_folder_by_slug(folder_slug)
        assert folder is not None
        record = self._visible_record(actor, folder_slug, doc_slug)
        self._require_author(actor, record)
        self._move(
            record,
            source=DocumentStatus.ARCHIVED,
            target=DocumentStatus.DRAFT,
            message="Only an archived document can be restored",
        )
        record.published_at = None
        record.updated_at = datetime.now(UTC)
        self._repo.save_document(record)
        return self._to_read(folder.slug, record)

    def delete_document(self, actor: UserRead, folder_slug: str, doc_slug: str) -> None:
        record = self._visible_record(actor, folder_slug, doc_slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.author_id:
            raise ForbiddenError("Only the author or an admin can delete this document")
        self._repo.delete_document(record.id)

    def list_revisions(
        self,
        actor: UserRead,
        folder_slug: str,
        doc_slug: str,
    ) -> list[RevisionRead]:
        record = self._visible_record(actor, folder_slug, doc_slug)
        self._require_author(actor, record)
        return [
            RevisionRead(
                version=rev.version,
                title=rev.title,
                body=rev.body,
                published_at=rev.published_at,
            )
            for rev in self._repo.list_revisions(record.id)
        ]

    def list_tags(self) -> list[TagCount]:
        counts: dict[str, int] = {}
        for doc in self._repo.list_documents():
            if doc.status is not DocumentStatus.PUBLISHED:
                continue
            for tag in doc.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [TagCount(name=name, document_count=counts[name]) for name in sorted(counts)]

    def _visible_record(
        self,
        actor: UserRead | None,
        folder_slug: str,
        doc_slug: str,
    ) -> DocumentRecord:
        folder = self._repo.get_folder_by_slug(folder_slug)
        if folder is None:
            raise NotFoundError("Folder", folder_slug)
        record = self._repo.get_document_in_folder(folder.id, doc_slug)
        if record is None or not _can_view(actor, record):
            raise NotFoundError("Document", doc_slug)
        return record

    def _owned_folder(self, actor: UserRead, folder_slug: str):
        folder = self._repo.get_folder_by_slug(folder_slug)
        if folder is None or folder.owner_id != actor.id:
            raise NotFoundError("Folder", folder_slug)
        return folder

    def _matches(
        self,
        doc: DocumentRecord,
        tag: str | None,
        folder_slug: str | None,
        query: str | None,
    ) -> bool:
        folder = self._repo.get_folder(doc.folder_id)
        if folder is None:
            return False
        if folder_slug is not None and folder.slug != folder_slug:
            return False
        if tag is not None and tag.strip().casefold() not in doc.tags:
            return False
        if query is not None:
            needle = query.casefold()
            haystack = f"{doc.title}\n{doc.summary}\n{doc.body}".casefold()
            if needle not in haystack:
                return False
        return True

    def _page(
        self,
        folder_slug: str,
        rows: list[DocumentRecord],
        *,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        return DocumentPage(
            items=[self._to_read(folder_slug, doc) for doc in rows[offset : offset + limit]],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def _page_global(
        self,
        rows: list[DocumentRecord],
        *,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        items: list[DocumentRead] = []
        for doc in rows[offset : offset + limit]:
            folder = self._repo.get_folder(doc.folder_id)
            assert folder is not None
            items.append(self._to_read(folder.slug, doc))
        return DocumentPage(items=items, total=len(rows), limit=limit, offset=offset)

    def _to_read(self, folder_slug: str, record: DocumentRecord) -> DocumentRead:
        author = self._users.get_by_id(record.author_id)
        return DocumentRead(
            id=record.id,
            folder_slug=folder_slug,
            slug=record.slug,
            title=record.title,
            summary=record.summary,
            body=record.body,
            status=record.status,
            tags=list(record.tags),
            author_id=record.author_id,
            author_name=author.full_name if author is not None else "Unknown",
            version=record.version,
            created_at=record.created_at,
            updated_at=record.updated_at,
            published_at=record.published_at,
        )

    @staticmethod
    def _require_author(actor: UserRead, record: DocumentRecord) -> None:
        if actor.id != record.author_id:
            raise ForbiddenError("Only the author can edit this document")

    @staticmethod
    def _move(
        record: DocumentRecord,
        *,
        source: DocumentStatus,
        target: DocumentStatus,
        message: str,
    ) -> None:
        allowed = _TRANSITIONS[record.status]
        if record.status is not source or target not in allowed:
            raise ConflictError(f"{message}. This document is {record.status.value}")
        record.status = target
