import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.editor import DocumentRevision, SyncOutbox
from app.repositories.document_repository import DocumentRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.revision_repository import RevisionRepository
from app.schemas.editor import EditSubmit, RevisionRead, SyncStatus, TextPatch
from app.schemas.user import UserRead
from app.services.document_service import DocumentService


def _apply_patch(body: str, patch: TextPatch) -> str:
    start = patch.start
    delete = patch.delete
    if start > len(body):
        raise ConflictError("Patch start is beyond document length")
    if start + delete > len(body):
        raise ConflictError("Patch delete span exceeds document length")
    return body[:start] + patch.insert + body[start + delete :]


class EditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._revisions = RevisionRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._document_service = DocumentService(session)

    async def list_revisions(
        self,
        actor: UserRead,
        slug: str,
        *,
        after_revision: int,
        limit: int,
    ) -> list[RevisionRead]:
        document = await self._document_service.require_visible_document(actor, slug)
        rows = await self._revisions.list_after_revision(
            document.id,
            after_revision=after_revision,
            limit=limit,
        )
        return [self._to_revision_read(row) for row in rows]

    async def submit(
        self,
        actor: UserRead,
        slug: str,
        payload: EditSubmit,
        *,
        idempotency_key: str,
    ) -> RevisionRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        document = await self._document_service.require_editor_membership(actor, slug)
        if payload.base_revision != document.revision:
            raise ConflictError(
                f"Stale base_revision: expected {document.revision}, "
                f"got {payload.base_revision}"
            )

        new_body = _apply_patch(document.body, payload.patch)
        now = datetime.now(UTC)
        new_revision_number = document.revision + 1
        document.body = new_body
        document.revision = new_revision_number
        document.updated_at = now

        patch_payload = payload.patch.model_dump()
        revision_row = DocumentRevision(
            document_id=document.id,
            author_id=actor.id,
            revision=new_revision_number,
            base_revision=payload.base_revision,
            patch=patch_payload,
            created_at=now,
        )
        await self._revisions.add(revision_row)
        members = await self._documents.list_members(document.id)
        for member in members:
            if member.user_id == actor.id:
                continue
            await self._revisions.add_outbox(
                SyncOutbox(
                    revision_id=revision_row.id,
                    document_id=document.id,
                    recipient_id=member.user_id,
                    status=SyncStatus.PENDING.value,
                    version=1,
                    created_at=now,
                )
            )
        await self._documents.save()
        await self._session.commit()

        body = self._to_revision_read(revision_row)
        await self._store_idempotent(actor, idempotency_key, body)
        await self._session.commit()
        return body

    def _to_revision_read(self, row: DocumentRevision) -> RevisionRead:
        return RevisionRead(
            id=row.id,
            document_id=row.document_id,
            author_id=row.author_id,
            revision=row.revision,
            base_revision=row.base_revision,
            patch=TextPatch.model_validate(row.patch),
            created_at=row.created_at,
        )

    async def _load_idempotent(self, actor: UserRead, key: str) -> RevisionRead | None:
        record = await self._idempotency.get(key)
        if record is None:
            return None
        if record.user_id != actor.id:
            raise ConflictError("Idempotency-Key was used by another user")
        data = json.loads(record.response_json)
        return RevisionRead.model_validate(data)

    async def _store_idempotent(
        self,
        actor: UserRead,
        key: str,
        body: RevisionRead,
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=body.model_dump_json(),
            status_code=201,
        )
