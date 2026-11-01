from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.text_embeddings import (
    chunk_text,
    cosine_similarity,
    embed_text,
    embedding_from_json,
    embedding_to_json,
)
from app.models.rag import KnowledgeCollection, RagChunk, RagDocument
from app.repositories.rag_repository import RagRepository
from app.schemas.rag import (
    CitationRead,
    CollectionCreate,
    CollectionRead,
    DocumentCreate,
    DocumentRead,
    QueryRequest,
    QueryResponse,
)


class RagService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RagRepository(session)

    async def create_collection(
        self,
        *,
        tenant_id: int,
        payload: CollectionCreate,
    ) -> CollectionRead:
        if await self._repo.collection_slug_exists(tenant_id=tenant_id, slug=payload.slug):
            raise ConflictError(f"Collection slug {payload.slug!r} already exists")
        row = KnowledgeCollection(
            tenant_id=tenant_id,
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
        )
        await self._repo.add_collection(row)
        await self._session.commit()
        return CollectionRead.model_validate(row)

    async def list_collections(self, tenant_id: int) -> list[CollectionRead]:
        rows = await self._repo.list_collections(tenant_id)
        return [CollectionRead.model_validate(row) for row in rows]

    async def get_collection(self, *, tenant_id: int, slug: str) -> CollectionRead:
        row = await self._require_collection(tenant_id=tenant_id, slug=slug)
        return CollectionRead.model_validate(row)

    async def ingest_document(
        self,
        *,
        tenant_id: int,
        collection_slug: str,
        payload: DocumentCreate,
    ) -> DocumentRead:
        collection = await self._require_collection(tenant_id=tenant_id, slug=collection_slug)
        document = RagDocument(
            tenant_id=tenant_id,
            collection_id=collection.id,
            title=payload.title,
            source_uri=payload.source_uri,
            raw_text=payload.text,
        )
        await self._repo.add_document(document)

        chunks_text = chunk_text(payload.text)
        chunk_rows: list[RagChunk] = []
        for index, content in enumerate(chunks_text):
            chunk_rows.append(
                RagChunk(
                    tenant_id=tenant_id,
                    collection_id=collection.id,
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                    embedding_json=embedding_to_json(embed_text(content)),
                )
            )
        if chunk_rows:
            await self._repo.add_chunks(chunk_rows)

        await self._session.commit()
        return DocumentRead(
            id=document.id,
            collection_id=document.collection_id,
            title=document.title,
            source_uri=document.source_uri,
            chunk_count=len(chunk_rows),
            created_at=document.created_at,
        )

    async def list_documents(
        self,
        *,
        tenant_id: int,
        collection_slug: str,
    ) -> list[DocumentRead]:
        collection = await self._require_collection(tenant_id=tenant_id, slug=collection_slug)
        documents = await self._repo.list_documents(
            tenant_id=tenant_id,
            collection_id=collection.id,
        )
        reads: list[DocumentRead] = []
        for document in documents:
            count = await self._repo.chunk_count(document.id)
            reads.append(
                DocumentRead(
                    id=document.id,
                    collection_id=document.collection_id,
                    title=document.title,
                    source_uri=document.source_uri,
                    chunk_count=count,
                    created_at=document.created_at,
                )
            )
        return reads

    async def query(
        self,
        *,
        tenant_id: int,
        collection_slug: str,
        payload: QueryRequest,
    ) -> QueryResponse:
        collection = await self._require_collection(tenant_id=tenant_id, slug=collection_slug)
        chunks = await self._repo.list_chunks_for_collection(
            tenant_id=tenant_id,
            collection_id=collection.id,
        )
        if not chunks:
            raise NotFoundError("Chunks", collection_slug)

        query_vector = embed_text(payload.question)
        scored: list[tuple[RagChunk, float]] = []
        for chunk in chunks:
            vector = embedding_from_json(chunk.embedding_json)
            scored.append((chunk, cosine_similarity(query_vector, vector)))
        scored.sort(key=lambda item: item[1], reverse=True)
        top = scored[: payload.top_k]

        citations: list[CitationRead] = []
        excerpts: list[str] = []
        for chunk, score in top:
            document = await self._repo.get_document(chunk.document_id)
            title = document.title if document else "Unknown"
            excerpt = chunk.content[:240]
            citations.append(
                CitationRead(
                    document_id=chunk.document_id,
                    document_title=title,
                    chunk_index=chunk.chunk_index,
                    excerpt=excerpt,
                    score=round(score, 4),
                )
            )
            excerpts.append(f"[{title}] {excerpt}")

        answer = (
            f"Retrieved {len(citations)} chunk(s) for your question. "
            + " ".join(excerpts)
        )
        return QueryResponse(
            collection_slug=collection.slug,
            question=payload.question,
            answer=answer,
            citations=citations,
        )

    async def _require_collection(self, *, tenant_id: int, slug: str) -> KnowledgeCollection:
        row = await self._repo.get_collection(tenant_id=tenant_id, slug=slug.lower())
        if row is None:
            raise NotFoundError("Collection", slug)
        return row
