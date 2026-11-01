from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KnowledgeCollection(Base):
    __tablename__ = "knowledge_collections"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_collection_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200))
    source_uri: Mapped[str] = mapped_column(String(500), default="")
    raw_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("rag_documents.id", ondelete="CASCADE"),
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
