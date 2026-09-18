"""Add thong_bao_lich table for schedule SLA notifications.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-18
"""

from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bảng thông báo lịch (SLA escalation worker). Trước đây chỉ được tạo trong
    # nhánh SQLite của init_db() (persist.py), KHÔNG có trong _ensure_scheduling_schema
    # và KHÔNG có Alembic migration nào tạo nó → Postgres trả 500 ở /api/v1/lich/thong-bao.
    # Schema khớp với nhánh SQLite để thống nhất.
    op.execute("""
        CREATE TABLE IF NOT EXISTS thong_bao_lich (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL DEFAULT 'quan_01',
            tuan_iso TEXT NOT NULL,
            su_kien TEXT NOT NULL,
            tieu_de TEXT NOT NULL,
            noi_dung TEXT NOT NULL,
            url TEXT NOT NULL,
            nv_id TEXT NOT NULL,
            da_xem INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, tuan_iso, su_kien, nv_id)
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_thong_bao_lich_user
        ON thong_bao_lich(store_id, nv_id, da_xem, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_thong_bao_lich_user;")
    op.execute("DROP TABLE IF EXISTS thong_bao_lich;")