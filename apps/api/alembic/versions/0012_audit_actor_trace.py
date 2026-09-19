"""Add actor trace columns to audit and copilot_audit_log.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-17
"""

from __future__ import annotations

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # audit: phân loại tác nhân + agent + người điều khiển
    # An toàn: chỉ ALTER nếu bảng tồn tại (tránh fail khi production chưa có bảng).
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('public.audit') IS NOT NULL THEN
                ALTER TABLE audit ADD COLUMN IF NOT EXISTS actor_type TEXT NOT NULL DEFAULT 'human';
                ALTER TABLE audit ADD COLUMN IF NOT EXISTS agent_name TEXT;
                ALTER TABLE audit ADD COLUMN IF NOT EXISTS controller_user_id TEXT;
                CREATE INDEX IF NOT EXISTS idx_audit_actor_type ON audit(actor_type, at);
            END IF;
        END $$;
    """)

    # copilot_audit_log: agent + người điều khiển
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('public.copilot_audit_log') IS NOT NULL THEN
                ALTER TABLE copilot_audit_log ADD COLUMN IF NOT EXISTS agent_name TEXT;
                ALTER TABLE copilot_audit_log ADD COLUMN IF NOT EXISTS controller_user_id TEXT;
                CREATE INDEX IF NOT EXISTS idx_copilot_audit_agent ON copilot_audit_log(agent_name, timestamp);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_actor_type;")
    op.execute("DROP INDEX IF EXISTS idx_copilot_audit_agent;")
    op.execute("ALTER TABLE audit DROP COLUMN IF EXISTS actor_type;")
    op.execute("ALTER TABLE audit DROP COLUMN IF EXISTS agent_name;")
    op.execute("ALTER TABLE audit DROP COLUMN IF EXISTS controller_user_id;")
    op.execute("ALTER TABLE copilot_audit_log DROP COLUMN IF EXISTS agent_name;")
    op.execute("ALTER TABLE copilot_audit_log DROP COLUMN IF EXISTS controller_user_id;")