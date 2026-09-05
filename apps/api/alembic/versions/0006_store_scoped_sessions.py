"""Add store scope to users and sessions.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-05
"""

from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS store_id TEXT NOT NULL DEFAULT 'quan_01';")
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS store_id TEXT NOT NULL DEFAULT 'quan_01';")


def downgrade() -> None:
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS store_id;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS store_id;")