from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.editor import Document, DocumentMembership


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Document | None:
        stmt = select(Document).where(Document.slug == slug)
        return await self._session.scalar(stmt)

    async def list_public(self, *, limit: int, offset: int) -> list[Document]:
        rows = await self._session.scalars(
            select(Document)
            .where(
                Document.visibility == "public",
                Document.status == "active",
            )
            .order_by(Document.title)
            .limit(limit)
            .offset(offset)
        )
        return list(rows)

    async def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[Document]:
        rows = await self._session.scalars(
            select(Document)
            .join(DocumentMembership, DocumentMembership.document_id == Document.id)
            .where(DocumentMembership.user_id == user_id, Document.status == "active")
            .order_by(Document.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows)

    async def add(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.flush()
        return document

    async def membership(self, *, document_id: int, user_id: int) -> DocumentMembership | None:
        stmt = select(DocumentMembership).where(
            DocumentMembership.document_id == document_id,
            DocumentMembership.user_id == user_id,
        )
        return await self._session.scalar(stmt)

    async def list_members(self, document_id: int) -> list[DocumentMembership]:
        rows = await self._session.scalars(
            select(DocumentMembership).where(DocumentMembership.document_id == document_id)
        )
        return list(rows)

    async def add_member(self, membership: DocumentMembership) -> DocumentMembership:
        self._session.add(membership)
        await self._session.flush()
        return membership

    async def save(self) -> None:
        await self._session.flush()
