"""initial rate limiter schema

Revision ID: 001_initial
Revises:
Create Date: 2026-10-23

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
        "rate_limit_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
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
    op.create_index(op.f("ix_rate_limit_policies_key"), "rate_limit_policies", ["key"], unique=True)

    op.create_table(
        "rate_limit_clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("client_key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["rate_limit_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rate_limit_clients_key"), "rate_limit_clients", ["key"], unique=True)
    op.create_index(
        op.f("ix_rate_limit_clients_policy_id"),
        "rate_limit_clients",
        ["policy_id"],
    )

    op.create_table(
        "rate_limit_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["rate_limit_clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id",
            "subject_key",
            "window_start",
            name="uq_rate_counter",
        ),
    )
    op.create_index(
        op.f("ix_rate_limit_counters_client_id"),
        "rate_limit_counters",
        ["client_id"],
    )

    op.create_table(
        "rate_limit_idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["rate_limit_clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "idempotency_key", name="uq_rate_idempotency"),
    )
    op.create_index(
        op.f("ix_rate_limit_idempotency_records_client_id"),
        "rate_limit_idempotency_records",
        ["client_id"],
    )


def downgrade() -> None:
    op.drop_table("rate_limit_idempotency_records")
    op.drop_table("rate_limit_counters")
    op.drop_table("rate_limit_clients")
    op.drop_table("rate_limit_policies")
