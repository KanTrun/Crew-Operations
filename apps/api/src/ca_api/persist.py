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
PBKDF2_VONG = int(
    os.environ.get("NHIPQUAN_PBKDF2_VONG", "1000" if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION") else "240000")
)
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
    with _conn() as cx:
        # Luôn chạy DDL IF NOT EXISTS — thêm bảng mới (kenh_bind) không bị kẹt
        # vì cờ _INITIALIZED sớm trên DB cũ.
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
            CREATE TABLE IF NOT EXISTS kenh_bind (
                channel TEXT NOT NULL,
                external_user_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (channel, external_user_id)
            );
            CREATE TABLE IF NOT EXISTS kenh_bind_code (
                code TEXT PRIMARY KEY,
                nv_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS menu_mon (
                id TEXT PRIMARY KEY,
                ten TEXT NOT NULL,
                gia INTEGER NOT NULL,
                an INTEGER NOT NULL DEFAULT 0,
                bom TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS don_quay (
                id TEXT PRIMARY KEY,
                nv_id TEXT NOT NULL,
                trang_thai TEXT NOT NULL,
                thanh_toan TEXT NOT NULL,
                dong TEXT NOT NULL,
                ly_do_huy TEXT,
                luc TEXT NOT NULL
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
        _seed_menu_neu_trong(cx)
    _INITIALIZED = True


_MENU_MAC_DINH = (
    ("mon_den", "Cà phê đen", 25000, {"cafe_g": 18, "ly": 1}),
    ("mon_sua", "Cà phê sữa", 30000, {"cafe_g": 16, "sua_ml": 40, "ly": 1}),
    ("mon_tra", "Trà đào", 35000, {"dao_lat": 3, "ly": 1}),
    ("mon_da", "Bạc xỉu", 32000, {"cafe_g": 12, "sua_ml": 80, "ly": 1}),
)


def _seed_menu_neu_trong(cx: sqlite3.Connection) -> None:
    n = cx.execute("SELECT COUNT(*) FROM menu_mon").fetchone()[0]
    if int(n) > 0:
        return
    for mid, ten, gia, bom in _MENU_MAC_DINH:
        cx.execute(
            "INSERT INTO menu_mon(id, ten, gia, an, bom) VALUES (?,?,?,?,?)",
            (mid, ten, gia, 0, json.dumps(bom, ensure_ascii=False)),
        )


def kenh_bind_get(channel: str, external_user_id: str) -> str | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT nv_id FROM kenh_bind WHERE channel=? AND external_user_id=?",
            (channel, external_user_id),
        ).fetchone()
    return str(row[0]) if row else None


def kenh_bind_set(channel: str, external_user_id: str, nv_id: str) -> None:
    from datetime import datetime, timezone

    init_db()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO kenh_bind(channel, external_user_id, nv_id, created_at)
            VALUES (?,?,?,?)
            ON CONFLICT(channel, external_user_id) DO UPDATE SET nv_id=excluded.nv_id
            """,
            (channel, external_user_id, nv_id, now),
        )


def kenh_bind_list(nv_id: str | None = None) -> list[dict[str, str]]:
    init_db()
    with _conn() as cx:
        if nv_id:
            rows = cx.execute(
                "SELECT channel, external_user_id, nv_id, created_at FROM kenh_bind WHERE nv_id=?",
                (nv_id,),
            ).fetchall()
        else:
            rows = cx.execute(
                "SELECT channel, external_user_id, nv_id, created_at FROM kenh_bind"
            ).fetchall()
    return [
        {
            "channel": str(r[0]),
            "external_user_id": str(r[1]),
            "nv_id": str(r[2]),
            "created_at": str(r[3]),
        }
        for r in rows
    ]


_FAILED_BINDS: dict[str, list[float]] = {}


def kenh_bind_code_issue(nv_id: str) -> str:
    from datetime import datetime, timezone

    init_db()
    code = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            "INSERT INTO kenh_bind_code(code, nv_id, created_at) VALUES (?,?,?)",
            (code, nv_id, now),
        )
    return code


def kenh_bind_code_consume(code: str, channel: str, external_user_id: str, max_age_seconds: int = 300) -> str | None:
    import time
    from datetime import datetime, timezone
    now_ts = time.time()
    user_key = f"{channel}:{external_user_id}"

    # Rate limit: tối đa 5 lần sai trong 15 phút
    attempts = [t for t in _FAILED_BINDS.get(user_key, []) if now_ts - t < 900]
    if len(attempts) >= 5:
        return None

    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT nv_id, created_at FROM kenh_bind_code WHERE code=?", (code.strip().lower(),)
        ).fetchone()
        if not row:
            attempts.append(now_ts)
            _FAILED_BINDS[user_key] = attempts
            return None
        
        nv_id = str(row[0])
        created_at_str = str(row[1]) if len(row) > 1 else ""

        # Kiểm tra TTL
        if created_at_str:
            try:
                created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - created_dt).total_seconds()
                if age > max_age_seconds:
                    cx.execute("DELETE FROM kenh_bind_code WHERE code=?", (code.strip().lower(),))
                    attempts.append(now_ts)
                    _FAILED_BINDS[user_key] = attempts
                    return None
            except Exception:
                pass

        cx.execute("DELETE FROM kenh_bind_code WHERE code=?", (code.strip().lower(),))
        _FAILED_BINDS.pop(user_key, None)

    kenh_bind_set(channel, external_user_id, nv_id)
    return nv_id


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


def list_users() -> list[dict[str, str]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            "SELECT username, role, nv_id, display_name FROM users ORDER BY username"
        ).fetchall()
    return [
        {"username": str(r[0]), "role": str(r[1]), "nv_id": str(r[2]), "display_name": str(r[3])}
        for r in rows
    ]


class NangVaiLoi(ValueError):
    def __init__(self, ma: str) -> None:
        super().__init__(ma)
        self.ma = ma


def set_role(username: str, role: str) -> dict[str, str]:
    """Chủ quán nâng nhân viên lên quản lý. Không tự phong chủ quán."""
    if role != "quan_ly":
        raise NangVaiLoi("vai_khong_hop_le")
    u = (username or "").strip().lower()
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT username, role, nv_id, display_name FROM users WHERE username=?", (u,)
        ).fetchone()
        if not row:
            raise NangVaiLoi("khong_co_tai_khoan")
        if row[1] == "chu_quan":
            raise NangVaiLoi("khong_doi_chu_quan")
        if row[1] == "quan_ly":
            return {
                "username": str(row[0]),
                "role": str(row[1]),
                "nv_id": str(row[2]),
                "display_name": str(row[3]),
            }
        if row[1] != "nhan_vien":
            raise NangVaiLoi("vai_khong_hop_le")
        cx.execute("UPDATE users SET role=? WHERE username=?", (role, u))
        cx.execute("UPDATE sessions SET role=? WHERE username=?", (role, u))
        return {
            "username": str(row[0]),
            "role": role,
            "nv_id": str(row[2]),
            "display_name": str(row[3]),
        }


def menu_list(*, gom_an: bool = False) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute("SELECT id, ten, gia, an, bom FROM menu_mon ORDER BY ten").fetchall()
    out = []
    for mid, ten, gia, an, bom in rows:
        if not gom_an and int(an):
            continue
        out.append(
            {
                "id": str(mid),
                "ten": str(ten),
                "gia": int(gia),
                "an": bool(an),
                "bom": json.loads(bom) if bom else {},
            }
        )
    return out


def menu_upsert(mon: dict[str, Any]) -> dict[str, Any]:
    init_db()
    mid = str(mon["id"]).strip()
    ten = str(mon["ten"]).strip()
    gia = int(mon["gia"])
    an = 1 if mon.get("an") else 0
    bom = json.dumps(mon.get("bom") or {}, ensure_ascii=False)
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO menu_mon(id, ten, gia, an, bom) VALUES (?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET ten=excluded.ten, gia=excluded.gia,
                an=excluded.an, bom=excluded.bom
            """,
            (mid, ten, gia, an, bom),
        )
    return {"id": mid, "ten": ten, "gia": gia, "an": bool(an), "bom": json.loads(bom)}


def menu_get(mon_id: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT id, ten, gia, an, bom FROM menu_mon WHERE id=?", (mon_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "ten": str(row[1]),
        "gia": int(row[2]),
        "an": bool(row[3]),
        "bom": json.loads(row[4]) if row[4] else {},
    }


def don_insert(don: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO don_quay(id, nv_id, trang_thai, thanh_toan, dong, ly_do_huy, luc)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                don["id"],
                don["nv_id"],
                don["trang_thai"],
                don["thanh_toan"],
                json.dumps(don["dong"], ensure_ascii=False),
                don.get("ly_do_huy"),
                don["luc"],
            ),
        )
    return don


def don_list(*, trang_thai: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        if trang_thai:
            rows = cx.execute(
                """
                SELECT id, nv_id, trang_thai, thanh_toan, dong, ly_do_huy, luc
                FROM don_quay WHERE trang_thai=? ORDER BY luc
                """,
                (trang_thai,),
            ).fetchall()
        else:
            rows = cx.execute(
                """
                SELECT id, nv_id, trang_thai, thanh_toan, dong, ly_do_huy, luc
                FROM don_quay ORDER BY luc DESC
                """
            ).fetchall()
    return [_don_row(r) for r in rows]


def don_get(don_id: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT id, nv_id, trang_thai, thanh_toan, dong, ly_do_huy, luc
            FROM don_quay WHERE id=?
            """,
            (don_id,),
        ).fetchone()
    return _don_row(row) if row else None


def don_update(don: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with _conn() as cx:
        cx.execute(
            """
            UPDATE don_quay SET trang_thai=?, thanh_toan=?, dong=?, ly_do_huy=?
            WHERE id=?
            """,
            (
                don["trang_thai"],
                don["thanh_toan"],
                json.dumps(don["dong"], ensure_ascii=False),
                don.get("ly_do_huy"),
                don["id"],
            ),
        )
    return don


def _don_row(r: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(r[0]),
        "nv_id": str(r[1]),
        "trang_thai": str(r[2]),
        "thanh_toan": str(r[3]),
        "dong": json.loads(r[4]),
        "ly_do_huy": r[5],
        "luc": str(r[6]),
        "nguon": "quay_noi_bo",
    }


def tieu_thu_append(item: dict[str, Any]) -> None:
    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(item)
        return rows

    kv_mutate("tieu_thu", mut, [])


def da_diem_danh(nv_id: str) -> bool:
    return nv_id in set(kv_get("diem_danh", []))


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
