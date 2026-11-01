from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.text_embeddings import chunk_text, embed_text, embedding_to_json
from app.models.membership import TenantMembership, TenantRole
from app.models.rag import KnowledgeCollection, RagChunk, RagDocument
from app.models.tenant import Tenant
from app.models.user import User

SEED_EMAIL = "demo@example.com"
SEED_PASSWORD = "DemoPass123!"
SEED_TENANT_SLUG = "acme-corp"
SEED_COLLECTION_SLUG = "product-docs"
SEED_DOC_TEXT = (
    "Refund policy: customers may request a full refund within 30 days of purchase. "
    "Enterprise plans include a 60-day satisfaction guarantee. "
    "Contact support@acme.example with your order id to start a refund."
)


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(select(User.id).where(User.email == SEED_EMAIL))
    if existing is not None:
        return

    user = User(
        email=SEED_EMAIL,
        hashed_password=hash_password(SEED_PASSWORD),
        full_name="Demo User",
    )
    tenant = Tenant(slug=SEED_TENANT_SLUG, name="Acme Corp")
    session.add_all([user, tenant])
    await session.flush()

    session.add(
        TenantMembership(
            tenant_id=tenant.id,
            user_id=user.id,
            role=TenantRole.OWNER.value,
        )
    )

    collection = KnowledgeCollection(
        tenant_id=tenant.id,
        slug=SEED_COLLECTION_SLUG,
        name="Product documentation",
        description="Policies and product copy for RAG demos.",
    )
    session.add(collection)
    await session.flush()

    document = RagDocument(
        tenant_id=tenant.id,
        collection_id=collection.id,
        title="Refund policy",
        source_uri="seed://refund-policy",
        raw_text=SEED_DOC_TEXT,
    )
    session.add(document)
    await session.flush()

    chunks = chunk_text(SEED_DOC_TEXT)
    session.add_all(
        [
            RagChunk(
                tenant_id=tenant.id,
                collection_id=collection.id,
                document_id=document.id,
                chunk_index=index,
                content=content,
                embedding_json=embedding_to_json(embed_text(content)),
            )
            for index, content in enumerate(chunks)
        ]
    )
    await session.commit()
