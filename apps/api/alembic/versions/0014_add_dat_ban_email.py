"""Add email column to dat_ban for reservation confirmation tickets.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-20
"""

from __future__ import annotations

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trước đây email của khách đặt bàn chỉ được nhét vào cột `notes`
    # (`effective_notes = f"Email: {email}. {notes}"` trong
    # table_reservation_service.atomic_hold_or_book_table). Điều này khiến
    # record đọc lại từ DB (reservation_get / reservation_find_active_by_psid)
    # KHÔNG có field `email` → send_reservation_confirmation_email không gửi
    # được phiếu xác nhận khi nhận record đọc từ DB.
    # Thêm cột `email` riêng để lưu nhất quán, đồng thời backfill từ `notes`.
    op.execute("""
        ALTER TABLE dat_ban ADD COLUMN email TEXT NOT NULL DEFAULT ''
    """)
    # Backfill: trích email đã lưu trong notes (dạng "Email: xxx@yyy.zz")
    op.execute("""
        UPDATE dat_ban
        SET email = substring(notes from 'Email:\\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,})')
        WHERE email = ''
          AND notes LIKE 'Email: %@%'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE dat_ban DROP COLUMN email")