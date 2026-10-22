from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    ingest_token_hash: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"
    __table_args__ = (UniqueConstraint("experiment_id", "key", name="uq_experiment_variant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    weight: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ExperimentEvent(Base):
    __tablename__ = "experiment_events"
    __table_args__ = (
        UniqueConstraint("experiment_id", "dedupe_key", name="uq_experiment_event_dedupe"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    variant_key: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ExperimentIdempotencyRecord(Base):
    __tablename__ = "experiment_idempotency_records"
    __table_args__ = (
        UniqueConstraint("experiment_id", "idempotency_key", name="uq_experiment_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128))
    response_json: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
