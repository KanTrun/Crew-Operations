# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Gate: mọi bảng mà mã nguồn dùng phải có migration Alembic.

Vì sao cần: nhánh SQLite của `persist.init_db()` tự tạo bảng, nhưng môi trường
PostgreSQL (Docker/production) chỉ chạy `alembic upgrade head`. Bảng nào chỉ
được thêm vào DDL SQLite mà quên migration sẽ tồn tại trên máy dev nhưng
KHÔNG tồn tại trên production → mọi endpoint chạm bảng đó trả 500
`UndefinedTable`.

Sự cố thật đã xảy ra: 8 bảng Gmail (`gmail_accounts`, `gmail_oauth_tokens`,
`gmail_sync_state`, `gmail_messages`, `gmail_labels`, `gmail_filters`) và trước
đó là `thong_bao_lich` (migration 0013).
"""

from __future__ import annotations

import re
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
PERSIST = API_ROOT / "src" / "ca_api" / "persist.py"
VERSIONS = API_ROOT / "alembic" / "versions"

# Bảng dùng chung giữa hai nhánh, không cần migration riêng.
# (rỗng — mọi bảng đều phải có migration)
_IGNORE: set[str] = set()


def _tables_created_in_sqlite_ddl() -> set[str]:
    """Tập bảng được CREATE trong `init_db()` (nhánh SQLite).

    Regex yêu cầu tên bảng theo sau là dấu `(` (đúng cú pháp CREATE TABLE), nên
    các câu SQL khác có chứa chuỗi tương tự trong comment/giá trị không bị bắt
    nhầm thành tên bảng.
    """
    src = PERSIST.read_text(encoding="utf-8")
    start = src.find("def init_db()")
    assert start != -1, "không tìm thấy init_db()"
    body = src[start:]
    return set(re.findall(r'CREATE TABLE IF NOT EXISTS\s+["`]?(\w+)["`]?\s*\(', body))


def _tables_created_on_all_backends() -> set[str]:
    """Bảng được tạo NGOÀI nhánh `if not _database_url()` ⇒ chạy cả Postgres.

    `_ensure_scheduling_schema()` được gọi ngay sau khối DDL SQLite và KHÔNG bị
    chặn bởi điều kiện backend, nên các bảng lịch/ca nó tạo tồn tại trên cả
    SQLite lẫn PostgreSQL — chúng không cần migration riêng.
    """
    src = PERSIST.read_text(encoding="utf-8")
    start = src.find("def _ensure_scheduling_schema(")
    assert start != -1, "không tìm thấy _ensure_scheduling_schema()"
    # Lấy tới hàm kế tiếp (khai báo top-level tiếp theo).
    rest = src[start:]
    nxt = rest.find("\ndef ", 10)
    body = rest[:nxt] if nxt != -1 else rest
    return set(re.findall(r'CREATE TABLE IF NOT EXISTS\s+["`]?(\w+)["`]?\s*\(', body))


def _tables_covered_by_migrations() -> set[str]:
    """Tập bảng được tạo trong bất kỳ file migration nào.

    Repo dùng CẢ HAI dạng: SQL thô qua `op.execute("CREATE TABLE ...")` (các
    migration 0009, 0013, 0015) và API Alembic `op.create_table("name", ...)`
    (migration 0008). Phải nhận diện cả hai, nếu không gate báo thiếu oan.
    """
    covered: set[str] = set()
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        # Dạng SQL thô.
        covered |= set(re.findall(r'CREATE TABLE (?:IF NOT EXISTS\s+)?"?(\w+)"?', text))
        # Dạng API Alembic: op.create_table("ten_bang", ...)
        covered |= set(re.findall(r'op\.create_table\(\s*"(\w+)"', text))
    return covered


def test_every_sqlite_table_has_migration() -> None:
    """Bảng nào tạo ở SQLite (chỉ nhánh SQLite) cũng phải tạo ở Postgres qua migration."""
    sqlite_only = _tables_created_in_sqlite_ddl() - _tables_created_on_all_backends() - _IGNORE
    migrated = _tables_covered_by_migrations()

    missing = sorted(sqlite_only - migrated)
    assert not missing, (
        "Các bảng sau có trong DDL SQLite nhưng THIẾU migration Alembic ⇒ "
        "PostgreSQL/production sẽ trả 500 UndefinedTable: " + ", ".join(missing)
    )


def test_all_backend_tables_are_reachable_on_postgres() -> None:
    """Mọi bảng dùng trong code phải tồn tại trên Postgres — qua migration HOẶC
    qua helper chạy trên mọi backend."""
    sqlite_tables = _tables_created_in_sqlite_ddl() - _IGNORE
    reachable = _tables_covered_by_migrations() | _tables_created_on_all_backends()

    missing = sorted(sqlite_tables - reachable)
    assert not missing, (
        "Bảng có trong DDL SQLite nhưng không có migration và cũng không nằm trong "
        "helper chạy mọi backend ⇒ thiếu trên PostgreSQL: " + ", ".join(missing)
    )


def test_migration_chain_is_linear_and_has_head() -> None:
    """Chuỗi revision phải liên tục: mỗi down_revision trỏ tới revision có thật."""
    revisions: dict[str, str | None] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        rev = re.search(r'^revision\s*=\s*"([^"]+)"', text, re.M)
        down = re.search(r'^down_revision\s*=\s*(?:"([^"]+)"|None)', text, re.M)
        if not rev:
            continue
        revisions[rev.group(1)] = down.group(1) if down and down.group(1) else None

    assert revisions, "không đọc được revision nào"

    referenced = {d for d in revisions.values() if d}
    heads = sorted(set(revisions) - referenced)
    assert len(heads) == 1, f"phải có đúng 1 head, đang có: {heads}"

    missing_parents = sorted(referenced - set(revisions))
    assert not missing_parents, f"down_revision trỏ tới revision không tồn tại: {missing_parents}"


def test_gmail_tables_have_migration() -> None:
    """Chốt riêng cho 8 bảng Gmail — sự cố thật đã xảy ra."""
    migrated = _tables_covered_by_migrations()
    for table in (
        "gmail_accounts",
        "gmail_oauth_tokens",
        "gmail_sync_state",
        "gmail_messages",
        "gmail_labels",
        "gmail_filters",
    ):
        assert table in migrated, f"bảng {table} thiếu migration Alembic"


def test_migration_has_downgrade() -> None:
    """Mọi migration phải có `downgrade()` để lùi được khi cần."""
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "def downgrade()" in text, f"{path.name} thiếu hàm downgrade()"
