"""initial experimentation schema

Revision ID: 001_initial
Revises:
Create Date: 2026-10-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ingest_token_hash", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_experiments_key"), "experiments", ["key"], unique=True)

    op.create_table(
        "experiment_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "key", name="uq_experiment_variant"),
    )
    op.create_index(
        op.f("ix_experiment_variants_experiment_id"),
        "experiment_variants",
        ["experiment_id"],
    )

    op.create_table(
        "experiment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("variant_key", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "dedupe_key", name="uq_experiment_event_dedupe"),
    )
    op.create_index(
        op.f("ix_experiment_events_experiment_id"),
        "experiment_events",
        ["experiment_id"],
    )
    op.create_index(
        op.f("ix_experiment_events_subject_id"), "experiment_events", ["subject_id"]
    )
    op.create_index(
        op.f("ix_experiment_events_event_type"), "experiment_events", ["event_type"]
    )
    op.create_index(
        op.f("ix_experiment_events_occurred_at"), "experiment_events", ["occurred_at"]
    )

    op.create_table(
        "experiment_idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id", "idempotency_key", name="uq_experiment_idempotency"
        ),
    )
    op.create_index(
        op.f("ix_experiment_idempotency_records_experiment_id"),
        "experiment_idempotency_records",
        ["experiment_id"],
    )


def downgrade() -> None:
    op.drop_table("experiment_idempotency_records")
    op.drop_table("experiment_events")
    op.drop_table("experiment_variants")
    op.drop_table("experiments")
