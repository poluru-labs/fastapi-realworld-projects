"""initial iot telemetry schema

Revision ID: 001_initial
Revises:
Create Date: 2026-10-20

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
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("site", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ingest_token_hash", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(op.f("ix_devices_key"), "devices", ["key"], unique=True)

    op.create_table(
        "telemetry_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "dedupe_key", name="uq_device_reading_dedupe"),
    )
    op.create_index(
        op.f("ix_telemetry_readings_device_id"), "telemetry_readings", ["device_id"], unique=False
    )
    op.create_index(
        op.f("ix_telemetry_readings_recorded_at"),
        "telemetry_readings",
        ["recorded_at"],
        unique=False,
    )

    op.create_table(
        "telemetry_idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "idempotency_key", name="uq_device_telemetry_idempotency"),
    )
    op.create_index(
        op.f("ix_telemetry_idempotency_records_device_id"),
        "telemetry_idempotency_records",
        ["device_id"],
        unique=False,
    )

    op.create_table(
        "telemetry_alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("comparator", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_telemetry_alert_rules_device_id"),
        "telemetry_alert_rules",
        ["device_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_telemetry_alert_rules_device_id"), table_name="telemetry_alert_rules")
    op.drop_table("telemetry_alert_rules")
    op.drop_index(
        op.f("ix_telemetry_idempotency_records_device_id"),
        table_name="telemetry_idempotency_records",
    )
    op.drop_table("telemetry_idempotency_records")
    op.drop_index(op.f("ix_telemetry_readings_recorded_at"), table_name="telemetry_readings")
    op.drop_index(op.f("ix_telemetry_readings_device_id"), table_name="telemetry_readings")
    op.drop_table("telemetry_readings")
    op.drop_index(op.f("ix_devices_key"), table_name="devices")
    op.drop_table("devices")
