"""Initial tables: nhan_vien, ca, lich_tuan_phan_cong.

Revision ID: 0001
Revises: —
Create Date: 2026-08-22
"""

from __future__ import annotations

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    op.execute("""
        CREATE TABLE IF NOT EXISTS nhan_vien (
            id          TEXT PRIMARY KEY,
            ten         TEXT NOT NULL,
            ky_nang     TEXT[] NOT NULL DEFAULT '{}',
            la_sinh_vien BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ca (
            id              TEXT PRIMARY KEY,
            ngay            DATE NOT NULL,
            bat_dau         TIME NOT NULL,
            ket_thuc        TIME NOT NULL,
            vi_tri          TEXT NOT NULL,
            so_nguoi_toi_thieu INTEGER NOT NULL DEFAULT 1,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS lich_tuan_phan_cong (
            id          SERIAL PRIMARY KEY,
            tuan_iso    TEXT NOT NULL,
            ca_id       TEXT NOT NULL REFERENCES ca(id) ON DELETE CASCADE,
            nv_id       TEXT NOT NULL REFERENCES nhan_vien(id) ON DELETE CASCADE,
            pinned      BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tuan_iso, ca_id, nv_id)
        );
    """)


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS lich_tuan_phan_cong;")
    op.execute("DROP TABLE IF EXISTS ca;")
    op.execute("DROP TABLE IF EXISTS nhan_vien;")
