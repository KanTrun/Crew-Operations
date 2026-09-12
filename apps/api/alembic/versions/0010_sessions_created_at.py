"""Add created_at to sessions for TTL enforcement.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-07
"""

from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_at TEXT NOT NULL DEFAULT '';")


def downgrade() -> None:
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS created_at;")
