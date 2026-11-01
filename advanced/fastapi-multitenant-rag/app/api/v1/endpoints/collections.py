from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import ActiveTenant, DbSession
from app.schemas.rag import (
    COLLECTION_SLUG_PATTERN,
    CollectionCreate,
    CollectionRead,
    DocumentCreate,
    DocumentRead,
    QueryRequest,
    QueryResponse,
)
from app.services.rag_service import RagService

router = APIRouter()

CollectionSlug = Annotated[
    str,
    Path(pattern=COLLECTION_SLUG_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[CollectionRead],
    summary="List knowledge collections",
    description="Every row is scoped to the active tenant from `X-Tenant-Slug`.",
)
async def list_collections(tenant: ActiveTenant, session: DbSession) -> list[CollectionRead]:
    return await RagService(session).list_collections(tenant.tenant.id)


@router.post(
    "",
    response_model=CollectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
    description="Collections group documents and vector chunks for retrieval.",
)
async def create_collection(
    tenant: ActiveTenant,
    session: DbSession,
    payload: CollectionCreate,
) -> CollectionRead:
    return await RagService(session).create_collection(tenant_id=tenant.tenant.id, payload=payload)


@router.get(
    "/{collection_slug}",
    response_model=CollectionRead,
    summary="Get collection metadata",
)
async def get_collection(
    tenant: ActiveTenant,
    session: DbSession,
    collection_slug: CollectionSlug,
) -> CollectionRead:
    return await RagService(session).get_collection(
        tenant_id=tenant.tenant.id,
        slug=collection_slug,
    )


@router.post(
    "/{collection_slug}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a text document",
    description=(
        "Splits text into overlapping chunks and stores deterministic demo embeddings. "
        "No external vector database — vectors live in SQL as JSON for teaching."
    ),
)
async def ingest_document(
    tenant: ActiveTenant,
    session: DbSession,
    collection_slug: CollectionSlug,
    payload: DocumentCreate,
) -> DocumentRead:
    return await RagService(session).ingest_document(
        tenant_id=tenant.tenant.id,
        collection_slug=collection_slug,
        payload=payload,
    )


@router.get(
    "/{collection_slug}/documents",
    response_model=list[DocumentRead],
    summary="List ingested documents",
)
async def list_documents(
    tenant: ActiveTenant,
    session: DbSession,
    collection_slug: CollectionSlug,
) -> list[DocumentRead]:
    return await RagService(session).list_documents(
        tenant_id=tenant.tenant.id,
        collection_slug=collection_slug,
    )


@router.post(
    "/{collection_slug}/query",
    response_model=QueryResponse,
    summary="Retrieve and answer from tenant knowledge",
    description=(
        "Embeds the question, ranks chunks with cosine similarity, and returns citations "
        "plus a stitched excerpt answer. Replace the answer step with an LLM in production."
    ),
)
async def query_collection(
    tenant: ActiveTenant,
    session: DbSession,
    collection_slug: CollectionSlug,
    payload: QueryRequest,
) -> QueryResponse:
    return await RagService(session).query(
        tenant_id=tenant.tenant.id,
        collection_slug=collection_slug,
        payload=payload,
    )
