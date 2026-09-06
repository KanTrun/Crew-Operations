"""Add enterprise chat tables and user status column.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Thêm cột status vào users nếu chưa có
    try:
        op.add_column("users", sa.Column("status", sa.Text(), nullable=False, server_default="active"))
    except Exception:
        pass

    # 2. Bảng chat_conversations
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("store_id", sa.Text(), nullable=False, server_default="quan_01"),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_chat_conv_store", "chat_conversations", ["store_id", "updated_at"])

    # 3. Bảng chat_participants
    op.create_table(
        "chat_participants",
        sa.Column("conversation_id", sa.Text(), sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("nv_id", sa.Text(), sa.ForeignKey("users.nv_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="member"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_chat_part_user", "chat_participants", ["nv_id", "status"])

    # 4. Bảng chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("conversation_id", sa.Text(), sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False, server_default="text"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("reply_to_id", sa.Text(), sa.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_unsent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_chat_msg_conv", "chat_messages", ["conversation_id", "created_at"])

    # 5. Bảng chat_reactions
    op.create_table(
        "chat_reactions",
        sa.Column("message_id", sa.Text(), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("nv_id", sa.Text(), sa.ForeignKey("users.nv_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("emoji", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. Bảng chat_read_receipts
    op.create_table(
        "chat_read_receipts",
        sa.Column("conversation_id", sa.Text(), sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("nv_id", sa.Text(), sa.ForeignKey("users.nv_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_read_message_id", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("chat_read_receipts")
    op.drop_table("chat_reactions")
    op.drop_table("chat_messages")
    op.drop_table("chat_participants")
    op.drop_table("chat_conversations")
    try:
        op.drop_column("users", "status")
    except Exception:
        pass
