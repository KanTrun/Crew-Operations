"""Persistent quán store — SQLite file, survives process restart."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]

_INITIALIZED = False

USERS = (
    ("lan", "nhipquan", "quan_ly", "nv_01", "Lan — quản lý"),
    ("minh", "nhipquan", "nhan_vien", "nv_03", "Minh — ca sáng"),
    ("hung", "nhipquan", "chu_quan", "nv_02", "Hùng — chủ quán"),
)

# ── Mật khẩu ──────────────────────────────────────────────────────────────
# Bản đầu hash SHA256 trần, không salt. Khi chỉ có 3 tài khoản fixture thì đó
# là nợ chấp nhận được; từ lúc mở màn hình đăng ký thì nó thành lỗ hổng thật
# (cùng mật khẩu → cùng digest, tra bảng rainbow ra ngay). Nên chuyển sang
# PBKDF2-HMAC-SHA256 có salt riêng từng tài khoản — vẫn thuần stdlib.
#
# Cột `password_sha` giữ nguyên tên để không phải migrate; nó lưu:
#   - "pbkdf2_sha256$<vòng>$<salt hex>$<hash hex>"  (bản mới)
#   - "<sha256 hex>"                                 (bản cũ, vẫn đăng nhập được)
PBKDF2_VONG = 240_000
_PREFIX = "pbkdf2_sha256"

# Vai trò người tự đăng ký. KHÔNG bao giờ là quan_ly/chu_quan: nếu tự đăng ký
# mà lấy được vai quản lý thì bất kỳ ai cũng duyệt được ràng buộc và phát được
# mã điểm danh. Nâng vai là việc của chủ quán, làm ngoài luồng đăng ký.
VAI_TU_DANG_KY = "nhan_vien"


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Băm mật khẩu bằng PBKDF2-HMAC-SHA256 kèm salt riêng."""
    s = salt if salt is not None else os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), s, PBKDF2_VONG)
    return f"{_PREFIX}${PBKDF2_VONG}${s.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """So mật khẩu với giá trị đã lưu. Chấp nhận cả bản cũ SHA256 trần."""
    if stored.startswith(f"{_PREFIX}$"):
        try:
            _, vong_raw, salt_hex, hash_hex = stored.split("$", 3)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), int(vong_raw)
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(dk.hex(), hash_hex)
    # Bản cũ: so bằng compare_digest để không lộ thông tin qua thời gian so sánh.
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)


def db_path() -> Path:
    override = os.environ.get("NHIPQUAN_DB")
    return Path(override) if override else ROOT / "data" / "quan.db"


def _conn() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(path, timeout=30)
    cx.execute("PRAGMA journal_mode=WAL")
    return cx


def init_db() -> None:
    global _INITIALIZED
    if _INITIALIZED and db_path().exists():
        return
    with _conn() as cx:
        cx.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_sha TEXT NOT NULL,
                role TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                nv_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kv (
                k TEXT PRIMARY KEY,
                v TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL,
                ai TEXT NOT NULL,
                hanh TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        for u, pw, role, nv, name in USERS:
            cx.execute(
                """
                INSERT OR IGNORE INTO users(username, password_sha, role, nv_id, display_name)
                VALUES (?,?,?,?,?)
                """,
                (u, hash_password(pw), role, nv, name),
            )
    _INITIALIZED = True


def reset_init_flag() -> None:
    """Tests may swap NHIPQUAN_DB between cases."""
    global _INITIALIZED
    _INITIALIZED = False


def login(username: str, password: str) -> dict[str, str] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT username, role, nv_id, display_name, password_sha
            FROM users WHERE username=?
            """,
            (username.strip().lower(),),
        ).fetchone()
        # Không tách "không có tài khoản" khỏi "sai mật khẩu": tách ra là cho
        # người ngoài dò được username nào tồn tại.
        if not row or not verify_password(password, row[4]):
            return None
        token = uuid.uuid4().hex
        cx.execute(
            "INSERT INTO sessions(token, username, role, nv_id) VALUES (?,?,?,?)",
            (token, row[0], row[1], row[2]),
        )
        return {
            "token": token,
            "role": row[1],
            "nv_id": row[2],
            "display_name": row[3],
        }


# ── Đăng ký ───────────────────────────────────────────────────────────────
_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,24}$")
MK_TOI_THIEU = 8


class DangKyLoi(ValueError):
    """Lỗi đăng ký có mã máy đọc được; tầng HTTP dịch thành câu tiếng Việt."""

    def __init__(self, ma: str) -> None:
        super().__init__(ma)
        self.ma = ma


def _nv_id_ke_tiep(cx: sqlite3.Connection) -> str:
    """Cấp mã nhân viên chưa dùng, dạng nv_XX."""
    dung = {
        r[0] for r in cx.execute("SELECT nv_id FROM users").fetchall() if isinstance(r[0], str)
    }
    i = 1
    while f"nv_{i:02d}" in dung:
        i += 1
    return f"nv_{i:02d}"


def register(username: str, password: str, display_name: str) -> dict[str, str]:
    """Tạo tài khoản nhân viên mới.

    Luôn cấp vai `nhan_vien` — xem `VAI_TU_DANG_KY`. Trả về đúng payload như
    `login()` để màn hình đăng ký vào được ngay, không phải đăng nhập lại.

    Raises:
        DangKyLoi: `ten_khong_hop_le` · `mat_khau_qua_ngan` · `thieu_ten_hien_thi`
            · `ten_da_ton_tai`
    """
    init_db()
    u = (username or "").strip().lower()
    ten = (display_name or "").strip()
    if not _USERNAME_RE.match(u):
        raise DangKyLoi("ten_khong_hop_le")
    if len(password or "") < MK_TOI_THIEU:
        raise DangKyLoi("mat_khau_qua_ngan")
    if not (2 <= len(ten) <= 60):
        raise DangKyLoi("thieu_ten_hien_thi")

    with _conn() as cx:
        cx.isolation_level = None
        cx.execute("BEGIN IMMEDIATE")
        try:
            if cx.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone():
                raise DangKyLoi("ten_da_ton_tai")
            nv = _nv_id_ke_tiep(cx)
            cx.execute(
                """
                INSERT INTO users(username, password_sha, role, nv_id, display_name)
                VALUES (?,?,?,?,?)
                """,
                (u, hash_password(password), VAI_TU_DANG_KY, nv, ten),
            )
            token = uuid.uuid4().hex
            cx.execute(
                "INSERT INTO sessions(token, username, role, nv_id) VALUES (?,?,?,?)",
                (token, u, VAI_TU_DANG_KY, nv),
            )
            cx.execute("COMMIT")
        except Exception:
            cx.execute("ROLLBACK")
            raise
    return {"token": token, "role": VAI_TU_DANG_KY, "nv_id": nv, "display_name": ten}


def session(authorization: str | None) -> dict[str, str] | None:
    init_db()
    if not authorization:
        return None
    raw = authorization.removeprefix("Bearer ").strip()
    with _conn() as cx:
        row = cx.execute(
            "SELECT username, role, nv_id FROM sessions WHERE token=?", (raw,)
        ).fetchone()
        if not row:
            return None
        return {"username": row[0], "role": row[1], "nv_id": row[2]}


def kv_get(key: str, default: Any) -> Any:
    init_db()
    with _conn() as cx:
        row = cx.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
    if not row:
        return default
    return json.loads(row[0])


def kv_set(key: str, value: Any) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def kv_mutate(key: str, fn: Callable[[Any], Any], default: Any) -> Any:
    """Atomic read-modify-write under BEGIN IMMEDIATE."""
    init_db()
    with _conn() as cx:
        cx.isolation_level = None
        cx.execute("BEGIN IMMEDIATE")
        try:
            row = cx.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
            cur = json.loads(row[0]) if row else default
            if isinstance(default, dict) and isinstance(cur, dict):
                cur = dict(cur)
            elif isinstance(default, list) and isinstance(cur, list):
                cur = list(cur)
            new = fn(cur)
            cx.execute(
                "INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, json.dumps(new, ensure_ascii=False)),
            )
            cx.execute("COMMIT")
            return new
        except Exception:
            cx.execute("ROLLBACK")
            raise


def audit_add(at: str, ai: str, hanh: str, payload: dict[str, Any]) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "INSERT INTO audit(at, ai, hanh, payload) VALUES (?,?,?,?)",
            (at, ai, hanh, json.dumps(payload, ensure_ascii=False)),
        )


def audit_list() -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute("SELECT at, ai, hanh, payload FROM audit ORDER BY id").fetchall()
    out = []
    for at, ai, hanh, payload in rows:
        item = json.loads(payload)
        item.update({"at": at, "ai": ai, "hanh": hanh})
        out.append(item)
    return out
