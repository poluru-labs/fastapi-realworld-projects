"""initial realtime analytics schema

Revision ID: 001_initial
Revises:
Create Date: 2026-10-19

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
        "event_streams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
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
    op.create_index(op.f("ix_event_streams_key"), "event_streams", ["key"], unique=True)

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["stream_id"], ["event_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "dedupe_key", name="uq_stream_event_dedupe"),
    )
    op.create_index(
        op.f("ix_analytics_events_stream_id"), "analytics_events", ["stream_id"], unique=False
    )
    op.create_index(
        op.f("ix_analytics_events_event_name"), "analytics_events", ["event_name"], unique=False
    )
    op.create_index(
        op.f("ix_analytics_events_occurred_at"), "analytics_events", ["occurred_at"], unique=False
    )

    op.create_table(
        "ingest_idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["stream_id"], ["event_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "idempotency_key", name="uq_stream_idempotency"),
    )
    op.create_index(
        op.f("ix_ingest_idempotency_records_stream_id"),
        "ingest_idempotency_records",
        ["stream_id"],
        unique=False,
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("threshold_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["stream_id"], ["event_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_rules_stream_id"), "alert_rules", ["stream_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alert_rules_stream_id"), table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_index(
        op.f("ix_ingest_idempotency_records_stream_id"), table_name="ingest_idempotency_records"
    )
    op.drop_table("ingest_idempotency_records")
    op.drop_index(op.f("ix_analytics_events_occurred_at"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_event_name"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_stream_id"), table_name="analytics_events")
    op.drop_table("analytics_events")
    op.drop_index(op.f("ix_event_streams_key"), table_name="event_streams")
    op.drop_table("event_streams")
