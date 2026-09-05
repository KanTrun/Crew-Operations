"""AI-learning record store and Facebook event-receipt idempotency.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-05
"""

from __future__ import annotations

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cột link review queue với bản generation AI đã duyệt — SQLite thêm sẵn
    # qua _migrate_schema, trên Postgres phải có ở đây.
    op.execute("ALTER TABLE fb_review_queue ADD COLUMN IF NOT EXISTS ai_generation_id TEXT;")
    op.execute("""
        CREATE TABLE IF NOT EXISTS fb_event_receipts (
            idempotency_key TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            page_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            external_event_id TEXT NOT NULL,
            processed_at TEXT NOT NULL
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fb_event_receipts_scope "
        "ON fb_event_receipts(store_id, page_id, event_type, processed_at);"
    )
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_generation_records (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, idempotency_key)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_generation_store_created "
        "ON ai_generation_records(store_id, created_at DESC);"
    )
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_feedback_events (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            generation_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, idempotency_key)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_feedback_store_generation "
        "ON ai_feedback_events(store_id, generation_id, created_at DESC);"
    )
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_evaluations (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            generation_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, idempotency_key)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_evaluation_store_generation "
        "ON ai_evaluations(store_id, generation_id, created_at DESC);"
    )
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_rule_proposals (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            version INTEGER NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(store_id, idempotency_key)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_rule_proposal_store_status "
        "ON ai_rule_proposals(store_id, status, updated_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ai_rule_proposal_store_status;")
    op.execute("DROP TABLE IF EXISTS ai_rule_proposals;")
    op.execute("DROP INDEX IF EXISTS idx_ai_evaluation_store_generation;")
    op.execute("DROP TABLE IF EXISTS ai_evaluations;")
    op.execute("DROP INDEX IF EXISTS idx_ai_feedback_store_generation;")
    op.execute("DROP TABLE IF EXISTS ai_feedback_events;")
    op.execute("DROP INDEX IF EXISTS idx_ai_generation_store_created;")
    op.execute("DROP TABLE IF EXISTS ai_generation_records;")
    op.execute("DROP INDEX IF EXISTS idx_fb_event_receipts_scope;")
    op.execute("DROP TABLE IF EXISTS fb_event_receipts;")
    op.execute("ALTER TABLE fb_review_queue DROP COLUMN IF EXISTS ai_generation_id;")
