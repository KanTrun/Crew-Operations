"""Add authoritative scheduling tables to Alembic chain.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-24
"""

from __future__ import annotations

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vì sao cần migration này: 5 bảng lịch chuẩn hoá (availability_confirmations,
    # schedule_runs, authoritative_assignments, open_shifts, shift_applications)
    # trước đây CHỈ được tạo lúc chạy bởi `persist._ensure_scheduling_schema()`.
    # Helper đó dùng `CREATE TABLE IF NOT EXISTS` nên:
    #   - DB Postgres đã có bảng ⇒ helper KHÔNG bao giờ thêm cột mới;
    #   - muốn đổi schema phải sửa code và restart, không có bản ghi phiên bản.
    # Đưa vào chuỗi migration để `alembic upgrade head` (chạy tự động trong
    # deploy AWS trước khi đổi container) là nguồn sự thật của schema, và để
    # cổng `test_migrations_complete.py` chặn mọi cột thêm sau này mà quên
    # migration → tránh 500 `UndefinedColumn` trên production.
    #
    # Ràng buộc kiểu dữ liệu: giữ TEXT cho timestamp/JSON đúng như helper runtime
    # và nhánh SQLite của `persist.py` (lưu ISO-8601 + json.dumps). KHÔNG đổi
    # sang TIMESTAMPTZ/JSONB: production hiện có cột TEXT, đổi kiểu sẽ lệch schema
    # giữa DB cũ và DB tạo mới.
    #
    # Mọi câu lệnh đều idempotent (`IF NOT EXISTS`) nên chạy lại vô hại trên
    # EC2 đã có bảng do helper tạo trước đó.

    # ── Xác nhận khả dụng theo tuần ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS availability_confirmations (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            nv_id TEXT NOT NULL,
            tuan_iso TEXT NOT NULL,
            availability TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(store_id, nv_id, tuan_iso)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_availability_week
        ON availability_confirmations(store_id, tuan_iso, nv_id, status)
    """)

    # ── Lần chạy solver (bản ghi bất biến của một tuần) ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS schedule_runs (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            tuan_iso TEXT NOT NULL,
            version INTEGER NOT NULL,
            status TEXT NOT NULL,
            input_snapshot TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            result_snapshot TEXT NOT NULL DEFAULT '{}',
            idempotency_key TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, tuan_iso, version),
            UNIQUE(store_id, tuan_iso, idempotency_key)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_schedule_runs_week
        ON schedule_runs(store_id, tuan_iso, version DESC)
    """)

    # ── Phân công có thẩm quyền của một lần chạy ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS authoritative_assignments (
            id TEXT PRIMARY KEY,
            schedule_run_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            tuan_iso TEXT NOT NULL,
            ca_id TEXT NOT NULL,
            nv_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(schedule_run_id, ca_id, nv_id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_authoritative_assignments_week
        ON authoritative_assignments(store_id, tuan_iso, ca_id, nv_id)
    """)

    # ── Ca trống chờ nhận (open shift) ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS open_shifts (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            schedule_run_id TEXT NOT NULL,
            tuan_iso TEXT NOT NULL,
            ca_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            deadline_at TEXT NOT NULL,
            claimed_by TEXT,
            claimed_at TEXT,
            escalated_at TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(store_id, schedule_run_id, ca_id)
        )
    """)

    # ── Đơn ứng ca của nhân viên ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS shift_applications (
            id TEXT PRIMARY KEY,
            open_shift_id TEXT NOT NULL,
            store_id TEXT NOT NULL,
            nv_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            decided_at TEXT,
            UNIQUE(open_shift_id, nv_id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_shift_applications_claim
        ON shift_applications(open_shift_id, status, created_at)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_shift_applications_claim")
    op.execute("DROP TABLE IF EXISTS shift_applications")
    op.execute("DROP TABLE IF EXISTS open_shifts")
    op.execute("DROP INDEX IF EXISTS idx_authoritative_assignments_week")
    op.execute("DROP TABLE IF EXISTS authoritative_assignments")
    op.execute("DROP INDEX IF EXISTS idx_schedule_runs_week")
    op.execute("DROP TABLE IF EXISTS schedule_runs")
    op.execute("DROP INDEX IF EXISTS idx_availability_week")
    op.execute("DROP TABLE IF EXISTS availability_confirmations")
