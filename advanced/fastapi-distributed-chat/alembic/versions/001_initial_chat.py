"""initial distributed chat schema

Revision ID: 001_initial
Revises:
Create Date: 2026-10-17

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
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        op.f("ix_idempotency_records_user_id"), "idempotency_records", ["user_id"], unique=False
    )

    op.create_table(
        "chat_rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("message_sequence", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_rooms_slug"), "chat_rooms", ["slug"], unique=True)
    op.create_index(op.f("ix_chat_rooms_owner_id"), "chat_rooms", ["owner_id"], unique=False)

    op.create_table(
        "room_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("last_read_sequence", sa.Integer(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id", name="uq_room_member"),
    )
    op.create_index(op.f("ix_room_memberships_room_id"), "room_memberships", ["room_id"])
    op.create_index(op.f("ix_room_memberships_user_id"), "room_memberships", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "sequence", name="uq_room_message_seq"),
    )
    op.create_index(op.f("ix_chat_messages_room_id"), "chat_messages", ["room_id"])
    op.create_index(op.f("ix_chat_messages_author_id"), "chat_messages", ["author_id"])

    op.create_table(
        "delivery_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("lease_holder", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_delivery_outbox_message_id"), "delivery_outbox", ["message_id"])
    op.create_index(op.f("ix_delivery_outbox_room_id"), "delivery_outbox", ["room_id"])
    op.create_index(op.f("ix_delivery_outbox_recipient_id"), "delivery_outbox", ["recipient_id"])
    op.create_index(op.f("ix_delivery_outbox_status"), "delivery_outbox", ["status"])
    op.create_index(op.f("ix_delivery_outbox_lease_holder"), "delivery_outbox", ["lease_holder"])

    op.create_table(
        "relay_nodes",
        sa.Column("relay_id", sa.String(length=64), nullable=False),
        sa.Column("registered_by_id", sa.Integer(), nullable=False),
        sa.Column("room_slugs", sa.JSON(), nullable=False),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["registered_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("relay_id"),
    )


def downgrade() -> None:
    op.drop_table("relay_nodes")
    op.drop_table("delivery_outbox")
    op.drop_table("chat_messages")
    op.drop_table("room_memberships")
    op.drop_table("chat_rooms")
    op.drop_table("idempotency_records")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
