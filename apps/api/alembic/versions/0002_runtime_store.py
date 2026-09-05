"""Create the operational runtime store used by the API and worker.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password_sha TEXT NOT NULL,
            role TEXT NOT NULL,
            nv_id TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            store_id TEXT NOT NULL DEFAULT 'quan_01'
        );
        CREATE TABLE sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            nv_id TEXT NOT NULL,
            store_id TEXT NOT NULL DEFAULT 'quan_01'
        );
        CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
        CREATE TABLE audit (
            id BIGSERIAL PRIMARY KEY,
            at TEXT NOT NULL,
            ai TEXT NOT NULL,
            hanh TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE kenh_bind (
            channel TEXT NOT NULL,
            external_user_id TEXT NOT NULL,
            nv_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (channel, external_user_id)
        );
        CREATE TABLE kenh_bind_code (
            code TEXT PRIMARY KEY,
            nv_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE menu_mon (
            id TEXT PRIMARY KEY,
            ten TEXT NOT NULL,
            gia INTEGER NOT NULL,
            an INTEGER NOT NULL DEFAULT 0,
            bom TEXT NOT NULL DEFAULT '{}',
            hinh_url TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE don_quay (
            id TEXT PRIMARY KEY,
            nv_id TEXT NOT NULL,
            trang_thai TEXT NOT NULL,
            thanh_toan TEXT NOT NULL,
            dong TEXT NOT NULL,
            ly_do_huy TEXT,
            luc TEXT NOT NULL
        );
        CREATE TABLE copilot_draft_actions (
            action_id TEXT PRIMARY KEY,
            intent TEXT NOT NULL,
            status TEXT NOT NULL,
            store_id TEXT NOT NULL,
            created_by TEXT NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            summary TEXT NOT NULL,
            explanation TEXT NOT NULL,
            payload_diff TEXT NOT NULL,
            requires_confirmation INTEGER NOT NULL,
            data_snapshot_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            executed_at TEXT,
            amended_from TEXT,
            amended_by TEXT
        );
        CREATE TABLE copilot_audit_log (
            id BIGSERIAL PRIMARY KEY,
            action_id TEXT NOT NULL,
            actor_user_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            intent TEXT NOT NULL,
            decision TEXT NOT NULL,
            payload_diff TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            channel TEXT NOT NULL,
            latency_ms INTEGER NOT NULL
        );
    """)


def downgrade() -> None:
    for table in (
        "copilot_audit_log",
        "copilot_draft_actions",
        "don_quay",
        "menu_mon",
        "kenh_bind_code",
        "kenh_bind",
        "audit",
        "kv",
        "sessions",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table};")