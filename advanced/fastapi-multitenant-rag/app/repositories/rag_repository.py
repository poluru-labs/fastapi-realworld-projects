from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import KnowledgeCollection, RagChunk, RagDocument


class RagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def collection_slug_exists(self, *, tenant_id: int, slug: str) -> bool:
        result = await self._session.execute(
            select(KnowledgeCollection.id).where(
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.slug == slug,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_collection(self, *, tenant_id: int, slug: str) -> KnowledgeCollection | None:
        result = await self._session.execute(
            select(KnowledgeCollection).where(
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def list_collections(self, tenant_id: int) -> list[KnowledgeCollection]:
        result = await self._session.scalars(
            select(KnowledgeCollection)
            .where(KnowledgeCollection.tenant_id == tenant_id)
            .order_by(KnowledgeCollection.slug)
        )
        return list(result)

    async def add_collection(self, collection: KnowledgeCollection) -> KnowledgeCollection:
        self._session.add(collection)
        await self._session.flush()
        return collection

    async def add_document(self, document: RagDocument) -> RagDocument:
        self._session.add(document)
        await self._session.flush()
        return document

    async def list_documents(self, *, tenant_id: int, collection_id: int) -> list[RagDocument]:
        result = await self._session.scalars(
            select(RagDocument)
            .where(
                RagDocument.tenant_id == tenant_id,
                RagDocument.collection_id == collection_id,
            )
            .order_by(RagDocument.id.desc())
        )
        return list(result)

    async def chunk_count(self, document_id: int) -> int:
        result = await self._session.scalar(
            select(func.count()).select_from(RagChunk).where(RagChunk.document_id == document_id)
        )
        return int(result or 0)

    async def add_chunks(self, chunks: list[RagChunk]) -> None:
        self._session.add_all(chunks)
        await self._session.flush()

    async def list_chunks_for_collection(
        self,
        *,
        tenant_id: int,
        collection_id: int,
    ) -> list[RagChunk]:
        result = await self._session.scalars(
            select(RagChunk).where(
                RagChunk.tenant_id == tenant_id,
                RagChunk.collection_id == collection_id,
            )
        )
        return list(result)

    async def get_document(self, document_id: int) -> RagDocument | None:
        return await self._session.get(RagDocument, document_id)
