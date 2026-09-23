"""Add Gmail management tables (accounts, tokens, sync, messages, labels, filters).

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-23
"""

from __future__ import annotations

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vì sao cần migration này: 8 bảng Gmail trước đây chỉ được tạo trong nhánh
    # SQLite của `persist.init_db()`. Ở môi trường PostgreSQL (Docker/production),
    # `init_db()` chỉ chạy `alembic upgrade head`, nên các bảng KHÔNG tồn tại và
    # mọi endpoint /api/v1/gmail/* trả 500 `UndefinedTable`.
    #
    # Ràng buộc kiểu dữ liệu: giữ TEXT cho timestamp/JSON để đồng nhất với
    # nhánh SQLite (persist.py lưu ISO-8601 và json.dumps).

    # ── Tài khoản Gmail ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS gmail_accounts (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL DEFAULT 'quan_01',
            nv_id TEXT NOT NULL,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            is_primary INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gmail_accounts_store_nv
        ON gmail_accounts(store_id, nv_id, is_active)
    """)

    # ── OAuth token (đã mã hoá Fernet trước khi ghi) ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS gmail_oauth_tokens (
            account_id TEXT PRIMARY KEY REFERENCES gmail_accounts(id) ON DELETE CASCADE,
            access_token_enc TEXT NOT NULL,
            refresh_token_enc TEXT,
            expires_at TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT '',
            token_type TEXT NOT NULL DEFAULT 'Bearer',
            updated_at TEXT NOT NULL
        )
    """)

    # ── Trạng thái đồng bộ ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS gmail_sync_state (
            account_id TEXT PRIMARY KEY REFERENCES gmail_accounts(id) ON DELETE CASCADE,
            last_history_id TEXT,
            last_sync_at TEXT,
            sync_cursor TEXT,
            total_messages INTEGER NOT NULL DEFAULT 0,
            unread_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)

    # ── Email đã đồng bộ ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS gmail_messages (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES gmail_accounts(id) ON DELETE CASCADE,
            thread_id TEXT NOT NULL,
            label_ids TEXT NOT NULL DEFAULT '[]',
            snippet TEXT NOT NULL DEFAULT '',
            from_email TEXT NOT NULL DEFAULT '',
            to_emails TEXT NOT NULL DEFAULT '[]',
            cc_emails TEXT NOT NULL DEFAULT '[]',
            subject TEXT NOT NULL DEFAULT '',
            body_text TEXT,
            body_html TEXT,
            internal_date TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            is_starred INTEGER NOT NULL DEFAULT 0,
            has_attachment INTEGER NOT NULL DEFAULT 0,
            raw_headers TEXT,
            created_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gmail_messages_account_thread
        ON gmail_messages(account_id, thread_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gmail_messages_account_date
        ON gmail_messages(account_id, internal_date DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gmail_messages_unread
        ON gmail_messages(account_id, is_read, internal_date DESC)
    """)

    # ── Nhãn ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS gmail_labels (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES gmail_accounts(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            label_type TEXT NOT NULL DEFAULT 'user',
            message_list_visibility TEXT NOT NULL DEFAULT 'show',
            label_list_visibility TEXT NOT NULL DEFAULT 'labelShow',
            color_background TEXT,
            color_text TEXT,
            total_messages INTEGER NOT NULL DEFAULT 0,
            unread_messages INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gmail_labels_account ON gmail_labels(account_id)
    """)

    # ── Bộ lọc ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS gmail_filters (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES gmail_accounts(id) ON DELETE CASCADE,
            criteria TEXT NOT NULL DEFAULT '{}',
            action TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gmail_filters_account ON gmail_filters(account_id)
    """)


def downgrade() -> None:
    # Thứ tự ngược để không vi phạm khoá ngoại.
    for table in (
        "gmail_filters",
        "gmail_labels",
        "gmail_messages",
        "gmail_sync_state",
        "gmail_oauth_tokens",
        "gmail_accounts",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
