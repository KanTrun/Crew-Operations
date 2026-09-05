"""Add table reservation and copilot receipt tables.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-06
"""

from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Copilot receipts
    op.execute("""
        CREATE TABLE IF NOT EXISTS copilot_execution_receipts (
            store_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            outcome TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            PRIMARY KEY (store_id, action_id, idempotency_key)
        );
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_copilot_receipt_action
        ON copilot_execution_receipts(store_id, action_id);
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS copilot_mail_delivery_receipts (
            store_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            outcome TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            PRIMARY KEY (store_id, idempotency_key)
        );
    """)

    # 2. Table reservation tables
    op.execute("""
        CREATE TABLE IF NOT EXISTS ban_an (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL DEFAULT 'quan_01',
            ten_ban TEXT NOT NULL,
            suc_chua INTEGER NOT NULL,
            vi_tri TEXT NOT NULL,
            can_combine_with TEXT NOT NULL DEFAULT '[]',
            trang_thai_hoat_dong INTEGER NOT NULL DEFAULT 1
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ban_an_store ON ban_an(store_id, trang_thai_hoat_dong);
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS dat_ban (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL DEFAULT 'quan_01',
            psid TEXT NOT NULL DEFAULT '',
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 120,
            party_size INTEGER NOT NULL,
            table_ids TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            source TEXT NOT NULL DEFAULT 'ai_auto',
            notes TEXT NOT NULL DEFAULT '',
            idempotency_key TEXT NOT NULL DEFAULT '',
            notified_nv_id TEXT,
            notification_acked_at TEXT,
            cancelled_by TEXT,
            cancelled_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_dat_ban_idem
        ON dat_ban(idempotency_key)
        WHERE status NOT IN ('cancelled', 'no_show') AND idempotency_key != '';
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dat_ban_time ON dat_ban(store_id, booking_time, status);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dat_ban_psid ON dat_ban(store_id, psid, status);
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS dat_ban_lich_su (
            id BIGSERIAL PRIMARY KEY,
            dat_ban_id TEXT NOT NULL,
            hanh_dong TEXT NOT NULL,
            trang_thai_cu TEXT,
            trang_thai_moi TEXT,
            thuc_hien_boi TEXT NOT NULL,
            ly_do TEXT NOT NULL DEFAULT '',
            thoi_gian TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS thong_bao_ca (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL DEFAULT 'quan_01',
            dat_ban_id TEXT NOT NULL,
            ca_id TEXT NOT NULL DEFAULT '',
            nv_id TEXT NOT NULL,
            tieu_de TEXT NOT NULL,
            noi_dung TEXT NOT NULL,
            da_xem INTEGER NOT NULL DEFAULT 0,
            escalated_at TEXT,
            created_at TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_thong_bao_ca_user
        ON thong_bao_ca(store_id, nv_id, da_xem, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_thong_bao_ca_user;")
    op.execute("DROP TABLE IF EXISTS thong_bao_ca;")
    op.execute("DROP TABLE IF EXISTS dat_ban_lich_su;")
    op.execute("DROP INDEX IF EXISTS idx_dat_ban_psid;")
    op.execute("DROP INDEX IF EXISTS idx_dat_ban_time;")
    op.execute("DROP INDEX IF EXISTS ux_dat_ban_idem;")
    op.execute("DROP TABLE IF EXISTS dat_ban;")
    op.execute("DROP INDEX IF EXISTS idx_ban_an_store;")
    op.execute("DROP TABLE IF EXISTS ban_an;")
    op.execute("DROP TABLE IF EXISTS copilot_mail_delivery_receipts;")
    op.execute("DROP INDEX IF EXISTS idx_copilot_receipt_action;")
    op.execute("DROP TABLE IF EXISTS copilot_execution_receipts;")
