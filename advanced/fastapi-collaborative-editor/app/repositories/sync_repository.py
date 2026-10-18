from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.editor import Document, SyncOutbox


class SyncRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, sync_id: int) -> SyncOutbox | None:
        return await self._session.get(SyncOutbox, sync_id)

    async def find_claimable(
        self,
        *,
        document_slugs: list[str],
        now: datetime,
    ) -> SyncOutbox | None:
        stmt = (
            select(SyncOutbox)
            .join(Document, Document.id == SyncOutbox.document_id)
            .where(
                SyncOutbox.status == "pending",
                or_(
                    SyncOutbox.lease_expires_at.is_(None),
                    SyncOutbox.lease_expires_at < now,
                ),
            )
            .order_by(SyncOutbox.created_at, SyncOutbox.id)
            .limit(1)
        )
        if document_slugs:
            stmt = stmt.where(Document.slug.in_(document_slugs))
        return await self._session.scalar(stmt)

    async def save(self) -> None:
        await self._session.flush()
