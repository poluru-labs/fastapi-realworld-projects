from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.editor import DocumentRevision, SyncOutbox


class RevisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_after_revision(
        self,
        document_id: int,
        *,
        after_revision: int,
        limit: int,
    ) -> list[DocumentRevision]:
        rows = await self._session.scalars(
            select(DocumentRevision)
            .where(
                DocumentRevision.document_id == document_id,
                DocumentRevision.revision > after_revision,
            )
            .order_by(DocumentRevision.revision)
            .limit(limit)
        )
        return list(rows)

    async def add(self, revision: DocumentRevision) -> DocumentRevision:
        self._session.add(revision)
        await self._session.flush()
        return revision

    async def add_outbox(self, row: SyncOutbox) -> None:
        self._session.add(row)

    async def save(self) -> None:
        await self._session.flush()
