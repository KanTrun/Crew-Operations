"""Add store_id to fb_review_queue for multi-store scoping.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-17
"""

from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE fb_review_queue ADD COLUMN IF NOT EXISTS store_id TEXT NOT NULL DEFAULT 'quan_01';"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fbrq_store ON fb_review_queue(store_id, status, created_at);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fbrq_store;")
    op.execute("ALTER TABLE fb_review_queue DROP COLUMN IF EXISTS store_id;")
