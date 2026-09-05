"""Add Facebook moderation review queue and webhook idempotency.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE chatbot_intent ADD COLUMN IF NOT EXISTS is_auto_safe INTEGER NOT NULL DEFAULT 0;")
    op.execute("""
        CREATE TABLE IF NOT EXISTS fb_review_queue (
            id BIGSERIAL PRIMARY KEY,
            source TEXT NOT NULL CHECK (source IN ('messenger', 'comment')),
            external_thread_id TEXT NOT NULL,
            external_psid TEXT NOT NULL,
            external_user_name TEXT,
            post_id TEXT,
            post_is_sensitive INTEGER NOT NULL DEFAULT 0,
            message_text TEXT NOT NULL,
            detected_intent TEXT NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            policy_action TEXT NOT NULL,
            assigned_role TEXT CHECK (assigned_role IN ('quan_ly', 'chu_quan')),
            proposed_response TEXT,
            flagged_reasons TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'edited_approved', 'rejected', 'sent', 'expired', 'auto_sent')),
            decided_by TEXT,
            decided_at TIMESTAMPTZ,
            final_response TEXT,
            audit_sent BIGINT,
            trace_id TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_fbrq_status ON fb_review_queue(status, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fbrq_role ON fb_review_queue(assigned_role, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fbrq_thread ON fb_review_queue(external_thread_id, created_at);")
    op.execute("""
        CREATE TABLE IF NOT EXISTS fb_escalation_log (
            id BIGSERIAL PRIMARY KEY,
            review_queue_id BIGINT NOT NULL REFERENCES fb_review_queue(id),
            escalated_to TEXT NOT NULL,
            reason TEXT NOT NULL,
            notified_channel TEXT,
            notified_at TIMESTAMPTZ,
            acked_at TIMESTAMPTZ
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS fb_psid_blacklist (
            psid TEXT PRIMARY KEY,
            strikes INTEGER NOT NULL DEFAULT 1,
            blocked_until TIMESTAMPTZ NOT NULL,
            reason TEXT
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS fb_processed_events (
            event_id TEXT PRIMARY KEY,
            processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fb_processed_events;")
    op.execute("DROP TABLE IF EXISTS fb_psid_blacklist;")
    op.execute("DROP TABLE IF EXISTS fb_escalation_log;")
    op.execute("DROP TABLE IF EXISTS fb_review_queue;")
    op.execute("ALTER TABLE chatbot_intent DROP COLUMN IF EXISTS is_auto_safe;")