"""Store Facebook customer event time for messaging-window enforcement.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE fb_review_queue ADD COLUMN IF NOT EXISTS event_at TIMESTAMPTZ;")


def downgrade() -> None:
    op.execute("ALTER TABLE fb_review_queue DROP COLUMN IF EXISTS event_at;")