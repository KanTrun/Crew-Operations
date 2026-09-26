# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Test shim `_PostgresConnection` — dịch cú pháp SQLite sang PostgreSQL.

Bug QA đợt 3 (2026-09-26): `GET /api/v1/chat/scheduler` trả HTTP 500 trên
production (Postgres). Nguyên nhân: nhiều hàm trong `persist.py` gọi
`cx.execute("COMMIT")` / `cx.execute("ROLLBACK")` theo phong cách SQLite, nhưng
psycopg3 CHẶN câu lệnh điều khiển giao dịch qua `cursor.execute()`.

Test này dùng connection giả để xác nhận shim dịch đúng mà không cần Postgres
thật (CI không có Postgres service cho unit test).
"""

from __future__ import annotations

from typing import Any

from ca_api.persist import _NullCursor, _PostgresConnection


class _FakePgCursor:
    """Giả cursor psycopg: ghi lại câu lệnh đã execute."""

    description: Any = None
    rowcount: int = 1

    def __init__(self, log: list[str]) -> None:
        self._log = log

    def fetchone(self) -> None:
        return None

    def fetchall(self) -> list[Any]:
        return []


class _FakePgConnection:
    """Giả psycopg connection: COMMIT/ROLLBACK phải gọi qua method, không execute."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self.committed = 0
        self.rolled_back = 0

    def execute(self, sql: str, params: Any = None) -> _FakePgCursor:
        # Bắt chước psycopg3: chặn câu lệnh điều khiển giao dịch qua execute.
        upper = sql.strip().rstrip(";").upper()
        if upper in {"COMMIT", "ROLLBACK", "BEGIN"}:
            raise RuntimeError(
                f"can't execute {upper} inside a transaction block; use method instead"
            )
        self.executed.append((sql, params))
        return _FakePgCursor([])

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def __enter__(self) -> _FakePgConnection:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def test_execute_commit_dich_sang_method() -> None:
    """`execute("COMMIT")` phải gọi connection.commit(), KHÔNG gửi SQL."""
    fake = _FakePgConnection()
    conn = _PostgresConnection(fake)
    conn.execute("COMMIT")
    assert fake.committed == 1, "phải gọi commit()"
    assert fake.executed == [], "không được gửi COMMIT dạng SQL"


def test_execute_rollback_dich_sang_method() -> None:
    fake = _FakePgConnection()
    conn = _PostgresConnection(fake)
    conn.execute("ROLLBACK")
    assert fake.rolled_back == 1
    assert fake.executed == []


def test_execute_begin_la_noop() -> None:
    """psycopg tự mở transaction → BEGIN không cần gửi, cũng không được lỗi."""
    fake = _FakePgConnection()
    conn = _PostgresConnection(fake)
    conn.execute("BEGIN IMMEDIATE")  # dạng SQLite phải được nuốt
    assert fake.executed == []


def test_cau_lenh_binh_thuong_van_di_qua() -> None:
    """SELECT/INSERT bình thường phải gửi SQL (đã dịch ? → %s)."""
    fake = _FakePgConnection()
    conn = _PostgresConnection(fake)
    conn.execute("SELECT id FROM users WHERE nv_id=?", ("nv_01",))
    assert len(fake.executed) == 1
    sql, params = fake.executed[0]
    assert "?" not in sql, "phải dịch ? sang %s cho psycopg"
    assert "%s" in sql
    assert params == ("nv_01",)


def test_commit_tra_ve_null_cursor_khong_vo() -> None:
    """Giá trị trả về của execute("COMMIT") phải dùng được (caller có thể đọc)."""
    fake = _FakePgConnection()
    conn = _PostgresConnection(fake)
    result = conn.execute("COMMIT")
    assert isinstance(result, type(conn.execute("BEGIN")))
    # Các thuộc tính mà _PostgresCursor đọc phải tồn tại
    assert result.rowcount == -1
    assert result.description is None
    assert result.fetchone() is None
    assert result.fetchall() == []


def test_null_cursor_du_thuoc_tinh() -> None:
    c = _NullCursor()
    assert c.description is None
    assert c.rowcount == -1
    assert c.fetchone() is None
    assert c.fetchall() == []
