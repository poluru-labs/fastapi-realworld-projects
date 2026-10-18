from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.editor import Document, DocumentMembership
from app.repositories.document_repository import DocumentRepository
from app.schemas.editor import (
    DocumentCreate,
    DocumentRead,
    DocumentStatus,
    DocumentUpdate,
    DocumentVisibility,
    MemberRole,
    MembershipRead,
    SeenRevisionUpdate,
)
from app.schemas.user import UserRead, UserRole


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)

    async def list_public(self, *, limit: int, offset: int) -> list[DocumentRead]:
        rows = await self._documents.list_public(limit=limit, offset=offset)
        return [DocumentRead.model_validate(r) for r in rows]

    async def list_mine(self, actor: UserRead, *, limit: int, offset: int) -> list[DocumentRead]:
        rows = await self._documents.list_for_user(actor.id, limit=limit, offset=offset)
        return [DocumentRead.model_validate(r) for r in rows]

    async def create(self, actor: UserRead, payload: DocumentCreate) -> DocumentRead:
        if await self._documents.get_by_slug(payload.slug) is not None:
            raise ConflictError("A document with this slug already exists")
        now = _utcnow()
        body = payload.body
        revision = 1 if body else 0
        document = Document(
            slug=payload.slug,
            title=payload.title,
            body=body,
            revision=revision,
            visibility=payload.visibility.value,
            status=DocumentStatus.ACTIVE.value,
            owner_id=actor.id,
            created_at=now,
            updated_at=now,
        )
        await self._documents.add(document)
        await self._documents.add_member(
            DocumentMembership(
                document_id=document.id,
                user_id=actor.id,
                role=MemberRole.EDITOR.value,
                last_seen_revision=revision,
            )
        )
        await self._session.commit()
        return DocumentRead.model_validate(document)

    async def get_document(self, actor: UserRead, slug: str) -> DocumentRead:
        record = await self._require_visible(actor, slug)
        return DocumentRead.model_validate(record)

    async def update_document(
        self,
        actor: UserRead,
        slug: str,
        payload: DocumentUpdate,
    ) -> DocumentRead:
        record = await self._require_visible(actor, slug)
        membership = await self._documents.membership(document_id=record.id, user_id=actor.id)
        is_editor = membership is not None and membership.role == MemberRole.EDITOR.value
        if actor.role is not UserRole.ADMIN and actor.id != record.owner_id and not is_editor:
            raise ForbiddenError("Only editors can rename this document")
        if payload.title is not None:
            record.title = payload.title
        record.updated_at = _utcnow()
        await self._documents.save()
        await self._session.commit()
        return DocumentRead.model_validate(record)

    async def join(self, actor: UserRead, slug: str) -> MembershipRead:
        record = await self._documents.get_by_slug(slug)
        if record is None or record.status != DocumentStatus.ACTIVE.value:
            raise NotFoundError("Document", slug)
        if record.visibility != DocumentVisibility.PUBLIC.value:
            raise NotFoundError("Document", slug)
        existing = await self._documents.membership(document_id=record.id, user_id=actor.id)
        if existing is not None:
            return MembershipRead.model_validate(existing)
        membership = DocumentMembership(
            document_id=record.id,
            user_id=actor.id,
            role=MemberRole.EDITOR.value,
            last_seen_revision=record.revision,
        )
        await self._documents.add_member(membership)
        await self._session.commit()
        return MembershipRead.model_validate(membership)

    async def archive(self, actor: UserRead, slug: str) -> DocumentRead:
        record = await self._require_visible(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.owner_id:
            raise ForbiddenError("Only the owner or an admin can archive a document")
        if record.status == DocumentStatus.ARCHIVED.value:
            raise ConflictError("Document is already archived")
        record.status = DocumentStatus.ARCHIVED.value
        record.updated_at = _utcnow()
        await self._documents.save()
        await self._session.commit()
        return DocumentRead.model_validate(record)

    async def update_seen_revision(
        self,
        actor: UserRead,
        slug: str,
        payload: SeenRevisionUpdate,
    ) -> MembershipRead:
        record = await self._require_visible(actor, slug)
        membership = await self._documents.membership(document_id=record.id, user_id=actor.id)
        if membership is None:
            raise NotFoundError("Membership", slug)
        if payload.last_seen_revision > record.revision:
            raise ConflictError("Cannot mark seen past the latest revision")
        membership.last_seen_revision = payload.last_seen_revision
        await self._documents.save()
        await self._session.commit()
        return MembershipRead.model_validate(membership)

    async def require_editor_membership(self, actor: UserRead, slug: str) -> Document:
        record = await self._require_visible(actor, slug)
        if record.status == DocumentStatus.ARCHIVED.value:
            raise ConflictError("Document is archived")
        membership = await self._documents.membership(document_id=record.id, user_id=actor.id)
        if membership is None:
            raise NotFoundError("Document", slug)
        if membership.role == MemberRole.VIEWER.value:
            raise ForbiddenError("Viewers cannot submit edits")
        return record

    async def require_visible_document(self, actor: UserRead, slug: str) -> Document:
        return await self._require_visible(actor, slug)

    async def _require_visible(self, actor: UserRead, slug: str) -> Document:
        record = await self._documents.get_by_slug(slug)
        if record is None:
            raise NotFoundError("Document", slug)
        if record.visibility == DocumentVisibility.PRIVATE.value:
            membership = await self._documents.membership(document_id=record.id, user_id=actor.id)
            if actor.role is not UserRole.ADMIN and membership is None:
                raise NotFoundError("Document", slug)
        return record
