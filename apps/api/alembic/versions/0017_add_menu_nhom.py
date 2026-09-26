"""Add menu_mon.nhom (product category) to Alembic chain.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-26
"""

from __future__ import annotations

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vì sao cần migration này: `menu_mon.nhom` (nhóm sản phẩm: ca_phe / tra /
    # sinh_to / banh / nuoc_dong_chai / nguyen_lieu) trước đây CHỈ được thêm ở
    # nhánh SQLite qua `persist._migrate_schema()` bằng `ALTER TABLE`.
    #
    # Ở môi trường PostgreSQL (Docker/production), `init_db()` không chạy
    # `_migrate_schema()` mà chỉ `alembic upgrade head`, nên cột sẽ KHÔNG tồn
    # tại và mọi truy vấn `SELECT ... nhom FROM menu_mon` trả
    # 500 `UndefinedColumn`.
    #
    # Ràng buộc kiểu dữ liệu: giữ TEXT đúng như nhánh SQLite. Mặc định '' nghĩa
    # là "chưa khai nhóm"; tầng đọc suy từ BOM để tương thích ngược với món cũ.
    #
    # Câu lệnh idempotent: chạy lại trên DB đã có cột là vô hại.
    op.execute(
        "ALTER TABLE menu_mon ADD COLUMN IF NOT EXISTS nhom TEXT NOT NULL DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE menu_mon DROP COLUMN IF EXISTS nhom")
