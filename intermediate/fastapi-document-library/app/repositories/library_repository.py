from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from app.schemas.document import DocumentStatus


@dataclass
class FolderRecord:
    id: int
    slug: str
    name: str
    description: str
    owner_id: int
    created_at: datetime


@dataclass
class DocumentRecord:
    id: int
    folder_id: int
    author_id: int
    slug: str
    title: str
    summary: str
    body: str
    status: DocumentStatus
    tags: list[str]
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


@dataclass
class RevisionRecord:
    document_id: int
    version: int
    title: str
    body: str
    published_at: datetime


def _seed() -> tuple[dict[int, FolderRecord], dict[int, DocumentRecord], list[RevisionRecord]]:
    folder_created = datetime.fromisoformat("2026-02-01T10:00:00+00:00")
    published_at = datetime.fromisoformat("2026-03-01T15:00:00+00:00")
    draft_at = datetime.fromisoformat("2026-03-02T15:00:00+00:00")

    folders = {
        1: FolderRecord(
            id=1,
            slug="product-docs",
            name="Product documentation",
            description="Customer-facing guides and release notes.",
            owner_id=2,
            created_at=folder_created,
        ),
        2: FolderRecord(
            id=2,
            slug="engineering",
            name="Engineering handbook",
            description="Internal standards and runbooks.",
            owner_id=2,
            created_at=folder_created,
        ),
    }
    documents = {
        1: DocumentRecord(
            id=1,
            folder_id=1,
            author_id=2,
            slug="getting-started",
            title="Getting started",
            summary="Onboard new users to the document library API.",
            body="Published documents are readable without a token. Drafts stay hidden.",
            status=DocumentStatus.PUBLISHED,
            tags=["onboarding", "docs"],
            version=1,
            created_at=published_at,
            updated_at=published_at,
            published_at=published_at,
        ),
        2: DocumentRecord(
            id=2,
            folder_id=1,
            author_id=2,
            slug="roadmap-draft",
            title="Roadmap draft",
            summary="Not visible on the public library index.",
            body="Try fetching this slug without a token to see a 404.",
            status=DocumentStatus.DRAFT,
            tags=["planning"],
            version=0,
            created_at=draft_at,
            updated_at=draft_at,
            published_at=None,
        ),
        3: DocumentRecord(
            id=3,
            folder_id=2,
            author_id=2,
            slug="api-standards",
            title="API standards",
            summary="How we design HTTP APIs at the company.",
            body="Use explicit status routes instead of boolean flags in PATCH bodies.",
            status=DocumentStatus.PUBLISHED,
            tags=["fastapi", "standards"],
            version=1,
            created_at=published_at,
            updated_at=published_at,
            published_at=published_at,
        ),
    }
    revisions = [
        RevisionRecord(
            document_id=1,
            version=1,
            title=documents[1].title,
            body=documents[1].body,
            published_at=published_at,
        ),
        RevisionRecord(
            document_id=3,
            version=1,
            title=documents[3].title,
            body=documents[3].body,
            published_at=published_at,
        ),
    ]
    return folders, documents, revisions


class LibraryRepository:
    def __init__(self) -> None:
        folders, documents, revisions = _seed()
        self._folders = folders
        self._documents = documents
        self._revisions = revisions
        self._doc_key: dict[tuple[int, str], int] = {
            (doc.folder_id, doc.slug): doc.id for doc in documents.values()
        }
        self._next_folder_id = max(self._folders.keys(), default=0) + 1
        self._next_document_id = max(self._documents.keys(), default=0) + 1

    def list_folders(self) -> list[FolderRecord]:
        return list(self._folders.values())

    def get_folder(self, folder_id: int) -> FolderRecord | None:
        return self._folders.get(folder_id)

    def get_folder_by_slug(self, slug: str) -> FolderRecord | None:
        for folder in self._folders.values():
            if folder.slug == slug:
                return folder
        return None

    def folder_slug_taken(self, slug: str) -> bool:
        return self.get_folder_by_slug(slug) is not None

    def add_folder(self, record: FolderRecord) -> FolderRecord:
        self._folders[record.id] = record
        return record

    def save_folder(self, record: FolderRecord) -> None:
        self._folders[record.id] = record

    def delete_folder(self, folder_id: int) -> None:
        doc_ids = [doc.id for doc in self._documents.values() if doc.folder_id == folder_id]
        for doc_id in doc_ids:
            self.delete_document(doc_id)
        self._folders.pop(folder_id, None)

    def allocate_folder_id(self) -> int:
        folder_id = self._next_folder_id
        self._next_folder_id += 1
        return folder_id

    def list_documents(self) -> list[DocumentRecord]:
        return list(self._documents.values())

    def list_documents_in_folder(self, folder_id: int) -> list[DocumentRecord]:
        return [doc for doc in self._documents.values() if doc.folder_id == folder_id]

    def get_document(self, document_id: int) -> DocumentRecord | None:
        return self._documents.get(document_id)

    def get_document_in_folder(self, folder_id: int, doc_slug: str) -> DocumentRecord | None:
        doc_id = self._doc_key.get((folder_id, doc_slug))
        if doc_id is None:
            return None
        return self._documents.get(doc_id)

    def document_slug_taken(self, folder_id: int, doc_slug: str) -> bool:
        return (folder_id, doc_slug) in self._doc_key

    def add_document(self, record: DocumentRecord) -> DocumentRecord:
        self._documents[record.id] = record
        self._doc_key[(record.folder_id, record.slug)] = record.id
        return record

    def save_document(self, record: DocumentRecord) -> None:
        self._documents[record.id] = record

    def delete_document(self, document_id: int) -> None:
        record = self._documents.pop(document_id, None)
        if record is not None:
            self._doc_key.pop((record.folder_id, record.slug), None)
            self._revisions = [rev for rev in self._revisions if rev.document_id != document_id]

    def allocate_document_id(self) -> int:
        document_id = self._next_document_id
        self._next_document_id += 1
        return document_id

    def add_revision(self, revision: RevisionRecord) -> None:
        self._revisions.append(revision)

    def list_revisions(self, document_id: int) -> list[RevisionRecord]:
        rows = [rev for rev in self._revisions if rev.document_id == document_id]
        rows.sort(key=lambda rev: rev.version, reverse=True)
        return rows


@lru_cache
def get_library_repository() -> LibraryRepository:
    return LibraryRepository()
