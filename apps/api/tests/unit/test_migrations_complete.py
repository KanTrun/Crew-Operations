# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Cổng: schema do mã nguồn tạo phải trùng schema do migration Alembic tạo.

Sự cố thật đã xảy ra NHIỀU LẦN, cùng một cơ chế:

1. `persist.init_db()` có hai nhánh. Nhánh SQLite tự chạy `executescript(...)`
   tạo bảng; nhánh PostgreSQL (Docker/production) **không chạy** DDL đó mà dựa
   hoàn toàn vào `alembic upgrade head`.
2. Bảng chỉ khai trong nhánh SQLite ⇒ production 500 `UndefinedTable`
   (8 bảng Gmail, `thong_bao_lich`, 5 bảng lịch ở migration 0016).
3. Cột chỉ thêm bằng `ALTER TABLE ... ADD COLUMN` trong `_migrate_schema()`
   ⇒ production 500 `UndefinedColumn`. Nguy hiểm hơn lỗi bảng vì cột nằm trong
   bảng ĐÃ tồn tại — `CREATE TABLE IF NOT EXISTS` không sửa được — và triệu
   chứng chỉ lộ khi endpoint chạm đúng cột đó.

Vì sao `_ensure_scheduling_schema()` không phải lưới an toàn: helper dùng
`CREATE TABLE IF NOT EXISTS` nên chỉ tạo bảng khi CHƯA có. DB production đã có
bảng ⇒ cột thêm về sau vào helper sẽ KHÔNG BAO GIỜ được áp. Migration là nguồn
sự thật duy nhất; helper chỉ là đường dự phòng lúc runtime.

Cổng đọc *cấu trúc thật* bằng parser quét ngoặc cân bằng (không regex thô), nên
bắt được cả bảng mới lẫn cột mới ở mọi nhánh DDL.
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

# Từ khoá mở đầu một ràng buộc — không phải khai báo cột.
_CONSTRAINT_STARTS = {
    "PRIMARY",
    "UNIQUE",
    "FOREIGN",
    "CHECK",
    "CONSTRAINT",
    "KEY",
    "EXCLUDE",
}


def _balanced(text: str, open_idx: int) -> str:
    """Trả phần trong cặp ngoặc bắt đầu tại `open_idx`.

    Quét cân bằng và bỏ qua nội dung chuỗi. Không dùng regex `\\(.*?\\)` vì
    tên kiểu như `NUMERIC(10, 2)` làm regex dừng sớm giữa khai báo bảng → bảng
    bị cắt cụt và cổng báo thiếu cột oan.
    """
    depth = 0
    i = open_idx
    while i < len(text):
        ch = text[i]
        if ch in "\"'":
            quote = ch * 3 if text.startswith(ch * 3, i) else ch
            i += len(quote)
            while i < len(text) and not text.startswith(quote, i):
                i += 1
            i += len(quote)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : i]
        i += 1
    raise AssertionError("ngoặc không cân bằng khi đọc khai báo bảng")


def _column_names(body: str) -> set[str]:
    """Tách tên cột ở cấp ngoặc ngoài cùng của khai báo bảng."""
    names: set[str] = set()
    buf: list[str] = []
    items: list[str] = []
    depth = 0
    i = 0
    while i < len(body):
        ch = body[i]
        if ch in "\"'":
            quote = ch * 3 if body.startswith(ch * 3, i) else ch
            j = i + len(quote)
            while j < len(body) and not body.startswith(quote, j):
                j += 1
            buf.append(body[i : j + len(quote)])
            i = j + len(quote)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    items.append("".join(buf))

    for item in items:
        head = item.strip().split(None, 1)
        if not head:
            continue
        name = head[0].strip('"`[]')
        # Chỉ nhận định danh hợp lệ. Lọc cả ràng buộc inline `UNIQUE(a, b)` và
        # chú thích đuôi dòng: nếu không, thông báo lỗi sẽ lẫn tên ràng buộc và
        # người đọc tưởng cổng báo sai.
        if not re.fullmatch(r"\w+", name):
            continue
        if name.upper() in _CONSTRAINT_STARTS:
            continue
        names.add(name)
    return names


def _schema(text: str) -> dict[str, set[str]]:
    """Bảng → tập cột, gom cả `CREATE TABLE` và `ALTER TABLE ... ADD COLUMN`."""
    out: dict[str, set[str]] = {}
    create = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["`]?(\w+)["`]?\s*\(',
        re.I,
    )
    for m in create.finditer(text):
        out.setdefault(m.group(1), set()).update(_column_names(_balanced(text, m.end() - 1)))

    alter = re.compile(
        r'ALTER\s+TABLE\s+["`]?(\w+)["`]?\s+ADD\s+COLUMN\s+'
        r'(?:IF\s+NOT\s+EXISTS\s+)?["`]?(\w+)["`]?',
        re.I,
    )
    for m in alter.finditer(text):
        out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def _function_body(name: str) -> str:
    """Thân hàm top-level `name` trong persist.py (tới `def` top-level kế tiếp)."""
    src = PERSIST.read_text(encoding="utf-8")
    start = src.find(f"def {name}(")
    assert start != -1, f"không tìm thấy {name}() trong persist.py"
    rest = src[start:]
    nxt = rest.find("\ndef ", 10)
    return rest[:nxt] if nxt != -1 else rest


def _tables_created_in_sqlite_ddl() -> set[str]:
    """Bảng chỉ tạo ở nhánh SQLite (DDL trong `_init_db_locked`)."""
    return set(_schema(_function_body("_init_db_locked")))


def _tables_created_on_all_backends() -> set[str]:
    """Bảng `_ensure_scheduling_schema()` tạo trên MỌI backend (kể cả Postgres)."""
    return set(_schema(_function_body("_ensure_scheduling_schema")))


def _sqlite_only_schema() -> dict[str, set[str]]:
    """Bảng/cột chỉ có ở nhánh SQLite (gồm cột `_migrate_schema` thêm)."""
    out = _schema(_function_body("_init_db_locked"))
    for table, cols in _schema(_function_body("_migrate_schema")).items():
        out.setdefault(table, set()).update(cols)
    return out


def _all_backend_schema() -> dict[str, set[str]]:
    """Bảng/cột `_ensure_scheduling_schema()` tạo trên mọi backend."""
    return _schema(_function_body("_ensure_scheduling_schema"))


def _migration_schema() -> dict[str, set[str]]:
    """Schema gom từ MỌI file migration, cả dạng SQL thô lẫn API Alembic."""
    merged: dict[str, set[str]] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for table, cols in _schema(text).items():
            merged.setdefault(table, set()).update(cols)

        # Dạng API: op.create_table("ten_bang", sa.Column("cot", ...), ...)
        for m in re.finditer(r"op\.create_table\(", text):
            call = _balanced(text, m.end() - 1)
            name = re.match(r'\s*"(\w+)"', call)
            if name:
                merged.setdefault(name.group(1), set()).update(
                    re.findall(r'sa\.Column\(\s*"(\w+)"', call)
                )

        # Dạng API: op.add_column("ten_bang", sa.Column("cot", ...))
        for m in re.finditer(r'op\.add_column\(\s*"(\w+)"\s*,\s*sa\.Column\(\s*"(\w+)"', text):
            merged.setdefault(m.group(1), set()).add(m.group(2))
    return merged


def _tables_covered_by_migrations() -> set[str]:
    """Tập bảng được tạo trong bất kỳ file migration nào.

    Repo dùng CẢ HAI dạng: SQL thô qua `op.execute("CREATE TABLE ...")` (các
    migration 0009, 0013, 0015, 0016) và API Alembic `op.create_table(...)`
    (migration 0008). Phải nhận diện cả hai, nếu không gate báo thiếu oan.
    """
    return set(_migration_schema())


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


def test_every_helper_table_has_migration() -> None:
    """Bảng của `_ensure_scheduling_schema()` phải có migration.

    Helper dùng `CREATE TABLE IF NOT EXISTS`: DB production đã có bảng thì nó
    không bao giờ sửa được schema nữa. Không có migration ⇒ mọi cột thêm về sau
    vào các bảng này chỉ tồn tại ở máy dev.
    """
    helper_tables = _tables_created_on_all_backends() - _IGNORE
    migrated = _tables_covered_by_migrations()

    missing = sorted(helper_tables - migrated)
    assert not missing, (
        "Các bảng trong _ensure_scheduling_schema() THIẾU migration Alembic ⇒ "
        "không thể tiến hoá schema trên production: " + ", ".join(missing)
    )


def test_every_sqlite_column_has_migration() -> None:
    """Cột khai trong DDL SQLite phải có trong migration.

    Thiếu ⇒ Postgres không có cột ⇒ 500 `UndefinedColumn` khi endpoint chạm cột đó.
    """
    migrated = _migration_schema()

    gaps: dict[str, list[str]] = {}
    for table, cols in sorted(_sqlite_only_schema().items()):
        if table in _IGNORE or table not in migrated:
            continue
        missing = sorted(cols - migrated[table])
        if missing:
            gaps[table] = missing

    assert not gaps, (
        "Các CỘT sau có trong DDL SQLite nhưng thiếu ở migration Alembic ⇒ "
        "production 500 UndefinedColumn: "
        + "; ".join(f"{t}: {c}" for t, c in gaps.items())
    )


def test_every_helper_column_has_migration() -> None:
    """Cột trong `_ensure_scheduling_schema()` phải có trong migration.

    Lỗ hổng cụ thể đã xảy ra: helper chỉ `CREATE TABLE IF NOT EXISTS`, nên cột
    thêm vào bảng ĐÃ tồn tại trên production sẽ không bao giờ được áp.
    """
    migrated = _migration_schema()

    gaps: dict[str, list[str]] = {}
    for table, cols in sorted(_all_backend_schema().items()):
        if table in _IGNORE:
            continue
        missing = sorted(cols - migrated.get(table, set()))
        if missing:
            gaps[table] = missing

    assert not gaps, (
        "Các CỘT trong _ensure_scheduling_schema() thiếu migration Alembic ⇒ "
        "chỉ tồn tại ở máy dev, production 500 UndefinedColumn: "
        + "; ".join(f"{t}: {c}" for t, c in gaps.items())
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


def test_scheduling_tables_have_migration() -> None:
    """Chốt riêng cho 5 bảng lịch — sự cố thật đã xảy ra (migration 0016).

    Trước 0016 chúng chỉ được tạo bởi `_ensure_scheduling_schema()`, tức không
    có bản ghi phiên bản: đổi schema phải sửa code rồi restart, và cột thêm vào
    bảng đã tồn tại sẽ không bao giờ được áp trên production.
    """
    migrated = _tables_covered_by_migrations()
    for table in (
        "availability_confirmations",
        "schedule_runs",
        "authoritative_assignments",
        "open_shifts",
        "shift_applications",
    ):
        assert table in migrated, f"bảng {table} thiếu migration Alembic"


def test_migration_has_downgrade() -> None:
    """Mọi migration phải có `downgrade()` để lùi được khi cần."""
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "def downgrade()" in text, f"{path.name} thiếu hàm downgrade()"
