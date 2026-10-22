"""initial location tracking schema

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
        "trackers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ingest_token_hash", sa.String(length=64), nullable=False),
        sa.Column("last_latitude", sa.Float(), nullable=True),
        sa.Column("last_longitude", sa.Float(), nullable=True),
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
    op.create_index(op.f("ix_trackers_key"), "trackers", ["key"], unique=True)

    op.create_table(
        "location_pings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracker_id", "dedupe_key", name="uq_tracker_ping_dedupe"),
    )
    op.create_index(op.f("ix_location_pings_tracker_id"), "location_pings", ["tracker_id"])
    op.create_index(op.f("ix_location_pings_recorded_at"), "location_pings", ["recorded_at"])

    op.create_table(
        "location_idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tracker_id", "idempotency_key", name="uq_tracker_location_idempotency"
        ),
    )
    op.create_index(
        op.f("ix_location_idempotency_records_tracker_id"),
        "location_idempotency_records",
        ["tracker_id"],
    )

    op.create_table(
        "geofences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("center_latitude", sa.Float(), nullable=False),
        sa.Column("center_longitude", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "geofence_monitors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("geofence_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["geofence_id"], ["geofences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracker_id", "geofence_id", name="uq_tracker_geofence"),
    )
    op.create_index(op.f("ix_geofence_monitors_tracker_id"), "geofence_monitors", ["tracker_id"])
    op.create_index(op.f("ix_geofence_monitors_geofence_id"), "geofence_monitors", ["geofence_id"])

    op.create_table(
        "geofence_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("geofence_id", sa.Integer(), nullable=False),
        sa.Column("inside", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["geofence_id"], ["geofences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracker_id", "geofence_id", name="uq_geofence_state"),
    )
    op.create_index(op.f("ix_geofence_states_tracker_id"), "geofence_states", ["tracker_id"])
    op.create_index(op.f("ix_geofence_states_geofence_id"), "geofence_states", ["geofence_id"])

    op.create_table(
        "geofence_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("geofence_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=8), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["geofence_id"], ["geofences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_geofence_events_tracker_id"), "geofence_events", ["tracker_id"])
    op.create_index(op.f("ix_geofence_events_occurred_at"), "geofence_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("geofence_events")
    op.drop_table("geofence_states")
    op.drop_table("geofence_monitors")
    op.drop_table("geofences")
    op.drop_table("location_idempotency_records")
    op.drop_table("location_pings")
    op.drop_table("trackers")
