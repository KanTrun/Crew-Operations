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

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
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
    os.environ.get(
        "NHIPQUAN_PBKDF2_VONG",
        "1000"
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION")
        else "240000",
    )
)
_PREFIX = "pbkdf2_sha256"

# Vai trò người tự đăng ký. KHÔNG bao giờ là quan_ly/chu_quan: nếu tự đăng ký
# mà lấy được vai quản lý thì bất kỳ ai cũng duyệt được ràng buộc và phát được
# mã điểm danh. Nâng vai là việc của chủ quán, làm ngoài luồng đăng ký.
VAI_TU_DANG_KY = "nhan_vien"
DEFAULT_STORE_ID = os.environ.get("NHIPQUAN_DEFAULT_STORE_ID", "quan_01").strip() or "quan_01"


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


_INITIALIZED_PATHS: set[str] = set()


def init_db() -> None:
    global _INITIALIZED
    p_str = str(db_path())
    if p_str in _INITIALIZED_PATHS:
        return
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
                display_name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                store_id TEXT NOT NULL DEFAULT 'quan_01'
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                store_id TEXT NOT NULL DEFAULT 'quan_01'
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
            CREATE TABLE IF NOT EXISTS copilot_draft_actions (
                action_id TEXT PRIMARY KEY,
                intent TEXT NOT NULL,
                status TEXT NOT NULL,
                store_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                confidence REAL NOT NULL,
                summary TEXT NOT NULL,
                explanation TEXT NOT NULL,
                payload_diff TEXT NOT NULL,
                requires_confirmation INTEGER NOT NULL,
                data_snapshot_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                amended_from TEXT,
                amended_by TEXT
            );
            CREATE TABLE IF NOT EXISTS copilot_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                intent TEXT NOT NULL,
                decision TEXT NOT NULL,
                payload_diff TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                channel TEXT NOT NULL,
                latency_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS copilot_execution_receipts (
                store_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                PRIMARY KEY (store_id, action_id, idempotency_key)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_copilot_receipt_action
                ON copilot_execution_receipts(store_id, action_id);
            CREATE TABLE IF NOT EXISTS copilot_mail_delivery_receipts (
                store_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                PRIMARY KEY (store_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS fb_review_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL CHECK (source IN ('messenger','comment')),
                external_thread_id TEXT NOT NULL,
                external_psid TEXT NOT NULL,
                external_user_name TEXT,
                post_id TEXT,
                post_is_sensitive INTEGER NOT NULL DEFAULT 0,
                message_text TEXT NOT NULL,
                detected_intent TEXT NOT NULL,
                confidence REAL NOT NULL,
                policy_action TEXT NOT NULL,
                assigned_role TEXT CHECK (assigned_role IN ('quan_ly','chu_quan')),
                proposed_response TEXT,
                ai_generation_id TEXT,
                flagged_reasons TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','edited_approved','rejected','sent','expired','auto_sent')),
                decided_by TEXT,
                decided_at TEXT,
                final_response TEXT,
                audit_sent INTEGER,
                trace_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_fbrq_status ON fb_review_queue(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_fbrq_role ON fb_review_queue(assigned_role, status);
            CREATE INDEX IF NOT EXISTS idx_fbrq_thread ON fb_review_queue(external_thread_id, created_at);
            CREATE TABLE IF NOT EXISTS fb_escalation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_queue_id INTEGER NOT NULL REFERENCES fb_review_queue(id),
                escalated_to TEXT NOT NULL,
                reason TEXT NOT NULL,
                notified_channel TEXT,
                notified_at TEXT,
                acked_at TEXT
            );
            CREATE TABLE IF NOT EXISTS fb_psid_blacklist (
                psid TEXT PRIMARY KEY,
                strikes INTEGER NOT NULL DEFAULT 1,
                blocked_until TEXT NOT NULL,
                reason TEXT
            );
            CREATE TABLE IF NOT EXISTS fb_processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fb_event_receipts (
                idempotency_key TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                page_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                external_event_id TEXT NOT NULL,
                processed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_fb_event_receipts_scope
                ON fb_event_receipts(store_id, page_id, event_type, processed_at);
            CREATE TABLE IF NOT EXISTS ai_generation_records (
                id TEXT PRIMARY KEY, store_id TEXT NOT NULL, channel TEXT NOT NULL,
                idempotency_key TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(store_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_ai_generation_store_created ON ai_generation_records(store_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS ai_feedback_events (
                id TEXT PRIMARY KEY, store_id TEXT NOT NULL, generation_id TEXT NOT NULL,
                channel TEXT NOT NULL, idempotency_key TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(store_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_ai_feedback_store_generation ON ai_feedback_events(store_id, generation_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS ai_evaluations (
                id TEXT PRIMARY KEY, store_id TEXT NOT NULL, generation_id TEXT NOT NULL,
                channel TEXT NOT NULL, idempotency_key TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(store_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_ai_evaluation_store_generation ON ai_evaluations(store_id, generation_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS ai_rule_proposals (
                id TEXT PRIMARY KEY, store_id TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
                version INTEGER NOT NULL, idempotency_key TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(store_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_ai_rule_proposal_store_status ON ai_rule_proposals(store_id, status, updated_at DESC);

            CREATE TABLE IF NOT EXISTS chat_conversations (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL DEFAULT 'quan_01',
                type TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                avatar_url TEXT,
                is_locked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_conv_store ON chat_conversations(store_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS chat_participants (
                conversation_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                status TEXT NOT NULL DEFAULT 'active',
                muted INTEGER NOT NULL DEFAULT 0,
                last_read_at TEXT,
                joined_at TEXT NOT NULL,
                archived_at TEXT,
                PRIMARY KEY (conversation_id, nv_id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_part_user ON chat_participants(nv_id, status);

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL DEFAULT '',
                reply_to_id TEXT,
                is_unsent INTEGER NOT NULL DEFAULT 0,
                edited_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_msg_conv ON chat_messages(conversation_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS chat_reactions (
                message_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                emoji TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (message_id, nv_id)
            );

            CREATE TABLE IF NOT EXISTS chat_read_receipts (
                conversation_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                last_read_message_id TEXT,
                read_at TEXT,
                PRIMARY KEY (conversation_id, nv_id)
            );

            CREATE TABLE IF NOT EXISTS ban_an (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL DEFAULT 'quan_01',
                ten_ban TEXT NOT NULL,
                suc_chua INTEGER NOT NULL,
                vi_tri TEXT NOT NULL,
                can_combine_with TEXT NOT NULL DEFAULT '[]',
                trang_thai_hoat_dong INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_ban_an_store ON ban_an(store_id, trang_thai_hoat_dong);

            CREATE TABLE IF NOT EXISTS dat_ban (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL DEFAULT 'quan_01',
                psid TEXT NOT NULL DEFAULT '',
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 120,
                party_size INTEGER NOT NULL,
                table_ids TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                source TEXT NOT NULL DEFAULT 'ai_auto',
                notes TEXT NOT NULL DEFAULT '',
                idempotency_key TEXT NOT NULL DEFAULT '',
                notified_nv_id TEXT,
                notification_acked_at TEXT,
                cancelled_by TEXT,
                cancelled_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ux_dat_ban_idem ON dat_ban(idempotency_key) WHERE status NOT IN ('cancelled', 'no_show') AND idempotency_key != '';
            CREATE INDEX IF NOT EXISTS idx_dat_ban_time ON dat_ban(store_id, booking_time, status);
            CREATE INDEX IF NOT EXISTS idx_dat_ban_psid ON dat_ban(store_id, psid, status);

            CREATE TABLE IF NOT EXISTS dat_ban_lich_su (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dat_ban_id TEXT NOT NULL,
                hanh_dong TEXT NOT NULL,
                trang_thai_cu TEXT,
                trang_thai_moi TEXT,
                thuc_hien_boi TEXT NOT NULL,
                ly_do TEXT NOT NULL DEFAULT '',
                thoi_gian TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS thong_bao_ca (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL DEFAULT 'quan_01',
                dat_ban_id TEXT NOT NULL,
                ca_id TEXT NOT NULL DEFAULT '',
                nv_id TEXT NOT NULL,
                tieu_de TEXT NOT NULL,
                noi_dung TEXT NOT NULL,
                da_xem INTEGER NOT NULL DEFAULT 0,
                escalated_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_thong_bao_ca_user ON thong_bao_ca(store_id, nv_id, da_xem, created_at DESC);
            """
        )
        _migrate_schema(cx)
        for u, pw, role, nv, name in USERS:
            cx.execute(
                """
                INSERT OR IGNORE INTO users(username, password_sha, role, nv_id, display_name, store_id, status)
                VALUES (?,?,?,?,?,?,'active')
                """,
                (u, hash_password(pw), role, nv, name, DEFAULT_STORE_ID),
            )
        _seed_menu_neu_trong(cx)
        _seed_chat_neu_trong(cx)
        _seed_tables_neu_trong(cx)
        _INITIALIZED_PATHS.add(p_str)
    _INITIALIZED = True


def _migrate_schema(cx: sqlite3.Connection) -> None:
    cols = {r[1] for r in cx.execute("PRAGMA table_info(menu_mon)")}
    if "hinh_url" not in cols:
        cx.execute("ALTER TABLE menu_mon ADD COLUMN hinh_url TEXT NOT NULL DEFAULT ''")
    ucols = {r[1] for r in cx.execute("PRAGMA table_info(users)")}
    if "email" not in ucols:
        cx.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    if "store_id" not in ucols:
        cx.execute("ALTER TABLE users ADD COLUMN store_id TEXT NOT NULL DEFAULT 'quan_01'")
    if "status" not in ucols:
        cx.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    cx.execute("UPDATE users SET store_id=? WHERE TRIM(store_id)=''", (DEFAULT_STORE_ID,))
    scols = {r[1] for r in cx.execute("PRAGMA table_info(sessions)")}
    if "store_id" not in scols:
        cx.execute("ALTER TABLE sessions ADD COLUMN store_id TEXT NOT NULL DEFAULT 'quan_01'")
    cx.execute("UPDATE sessions SET store_id=(SELECT store_id FROM users WHERE users.username=sessions.username) WHERE store_id='quan_01' AND EXISTS (SELECT 1 FROM users WHERE users.username=sessions.username)")
    evaluation_cols = {r[1] for r in cx.execute("PRAGMA table_info(ai_evaluations)")}
    if "idempotency_key" not in evaluation_cols:
        cx.execute("ALTER TABLE ai_evaluations ADD COLUMN idempotency_key TEXT NOT NULL DEFAULT ''")
        cx.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_evaluation_store_idem ON ai_evaluations(store_id, idempotency_key)")
    proposal_cols = {r[1] for r in cx.execute("PRAGMA table_info(ai_rule_proposals)")}
    if "idempotency_key" not in proposal_cols:
        cx.execute("ALTER TABLE ai_rule_proposals ADD COLUMN idempotency_key TEXT NOT NULL DEFAULT ''")
        cx.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_rule_proposal_store_idem ON ai_rule_proposals(store_id, idempotency_key)")
    review_cols = {r[1] for r in cx.execute("PRAGMA table_info(fb_review_queue)")}
    if "ai_generation_id" not in review_cols:
        cx.execute("ALTER TABLE fb_review_queue ADD COLUMN ai_generation_id TEXT")

    ccols = {r[1] for r in cx.execute("PRAGMA table_info(chat_conversations)")}
    if ccols and "display_name" not in ccols:
        cx.execute("DROP TABLE IF EXISTS chat_read_receipts")
        cx.execute("DROP TABLE IF EXISTS chat_reactions")
        cx.execute("DROP TABLE IF EXISTS chat_messages")
        cx.execute("DROP TABLE IF EXISTS chat_participants")
        cx.execute("DROP TABLE IF EXISTS chat_conversations")
        cx.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL DEFAULT 'quan_01',
                type TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                avatar_url TEXT,
                is_locked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_conv_store ON chat_conversations(store_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS chat_participants (
                conversation_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                status TEXT NOT NULL DEFAULT 'active',
                muted INTEGER NOT NULL DEFAULT 0,
                last_read_at TEXT,
                joined_at TEXT NOT NULL,
                archived_at TEXT,
                PRIMARY KEY (conversation_id, nv_id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_part_user ON chat_participants(nv_id, status);
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL DEFAULT '',
                reply_to_id TEXT,
                is_unsent INTEGER NOT NULL DEFAULT 0,
                edited_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_msg_conv ON chat_messages(conversation_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS chat_reactions (
                message_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                emoji TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (message_id, nv_id)
            );
            CREATE TABLE IF NOT EXISTS chat_read_receipts (
                conversation_id TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                last_read_message_id TEXT,
                read_at TEXT,
                PRIMARY KEY (conversation_id, nv_id)
            );
            """
        )


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
    from datetime import datetime

    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
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
    from datetime import datetime

    init_db()
    code = uuid.uuid4().hex[:8]
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            "INSERT INTO kenh_bind_code(code, nv_id, created_at) VALUES (?,?,?)",
            (code, nv_id, now),
        )
    return code


def kenh_bind_code_consume(
    code: str, channel: str, external_user_id: str, max_age_seconds: int = 300
) -> str | None:
    import time
    from datetime import datetime

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
                age = (datetime.now(UTC) - created_dt).total_seconds()
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
            SELECT username, role, nv_id, display_name, password_sha, store_id
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
            "INSERT INTO sessions(token, username, role, nv_id, store_id) VALUES (?,?,?,?,?)",
            (token, row[0], row[1], row[2], row[5]),
        )
        return {
            "token": token,
            "role": row[1],
            "nv_id": row[2],
            "display_name": row[3],
            "store_id": row[5],
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
    dung = {r[0] for r in cx.execute("SELECT nv_id FROM users").fetchall() if isinstance(r[0], str)}
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
    store_id = DEFAULT_STORE_ID
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
                INSERT INTO users(username, password_sha, role, nv_id, display_name, store_id, status)
                VALUES (?,?,?,?,?,?,'active')
                """,
                (u, hash_password(password), VAI_TU_DANG_KY, nv, ten, store_id),
            )
            token = uuid.uuid4().hex
            cx.execute(
                "INSERT INTO sessions(token, username, role, nv_id, store_id) VALUES (?,?,?,?,?)",
                (token, u, VAI_TU_DANG_KY, nv, store_id),
            )

            # Tự động đưa nhân viên mới vào Nhóm Chung Toàn Quán
            conv_general_id = f"conv_general_{store_id}"
            now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            cx.execute(
                """
                INSERT OR IGNORE INTO chat_conversations(id, store_id, type, display_name, avatar_url, is_locked, created_at, updated_at)
                VALUES (?,?,?,?,?,1,?,?)
                """,
                (conv_general_id, store_id, "general", "☕ NHỊP QUÁN · Hội Quán Chung", "", now_iso, now_iso),
            )
            cx.execute(
                """
                INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
                VALUES (?,?,'member','active',?)
                """,
                (conv_general_id, nv, now_iso),
            )
            # Tin nhắn hệ thống chào đón thành viên mới
            msg_welcome_id = f"msg_{uuid.uuid4().hex[:12]}"
            cx.execute(
                """
                INSERT INTO chat_messages(id, conversation_id, sender_id, type, content, is_unsent, created_at)
                VALUES (?,?,'system','system',?,0,?)
                """,
                (
                    msg_welcome_id,
                    conv_general_id,
                    f"🎉 Chào mừng {ten} gia nhập đại gia đình NHỊP QUÁN!",
                    now_iso,
                ),
            )
            cx.execute(
                "UPDATE chat_conversations SET updated_at = ? WHERE id = ?",
                (now_iso, conv_general_id),
            )

            cx.execute("COMMIT")
        except Exception:
            cx.execute("ROLLBACK")
            raise
    return {"token": token, "role": VAI_TU_DANG_KY, "nv_id": nv, "display_name": ten, "store_id": store_id}


def session(authorization: str | None) -> dict[str, str] | None:
    init_db()
    if not authorization:
        return None
    raw = authorization.removeprefix("Bearer ").strip()
    with _conn() as cx:
        row = cx.execute(
            "SELECT s.username, s.role, s.nv_id, u.email, s.store_id FROM sessions s "
            "LEFT JOIN users u ON u.nv_id = s.nv_id WHERE s.token=?",
            (raw,),
        ).fetchone()
        if not row:
            return None
        return {"username": row[0], "role": row[1], "nv_id": row[2], "email": str(row[3] or ""), "store_id": row[4]}


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


def copilot_commit_internal_execution(
    *,
    store_id: str,
    action_id: str,
    idempotency_key: str,
    intent: str,
    actor_user_id: str,
    payload_diff: dict[str, Any],
    outcome: dict[str, Any],
    kv_mutations: dict[str, tuple[Callable[[Any], Any], Any]],
    channel: str = "web",
    latency_ms: int = 0,
) -> bool:
    """Commit internal Copilot writes, action and audit in one transaction."""
    init_db()
    with _conn() as cx:
        cx.isolation_level = None
        cx.execute("BEGIN IMMEDIATE")
        try:
            receipt = cx.execute(
                "SELECT 1 FROM copilot_execution_receipts "
                "WHERE store_id=? AND action_id=? AND idempotency_key=? AND status='pending'",
                (store_id, action_id, idempotency_key),
            ).fetchone()
            if not receipt:
                raise RuntimeError("internal_execution_receipt_missing")

            for key, (mutator, default) in kv_mutations.items():
                row = cx.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
                current = json.loads(row[0]) if row else default
                if isinstance(default, dict) and isinstance(current, dict):
                    current = dict(current)
                elif isinstance(default, list) and isinstance(current, list):
                    current = list(current)
                updated = mutator(current)
                cx.execute(
                    "INSERT INTO kv(k,v) VALUES(?,?) "
                    "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                    (key, json.dumps(updated, ensure_ascii=False)),
                )

            draft_update = cx.execute(
                "UPDATE copilot_draft_actions SET status='executed', executed_at=? "
                "WHERE action_id=? AND store_id=? AND status='executing'",
                (_iso_now(), action_id, store_id),
            )
            if draft_update.rowcount != 1:
                raise RuntimeError("internal_execution_action_claim_missing")

            now_iso = _iso_now()
            cx.execute(
                "INSERT INTO copilot_audit_log(" 
                "action_id, actor_user_id, store_id, intent, decision, payload_diff, "
                "timestamp, channel, latency_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    action_id, actor_user_id, store_id, intent, "approve",
                    json.dumps(payload_diff, ensure_ascii=False), now_iso, channel, latency_ms,
                ),
            )
            receipt_update = cx.execute(
                "UPDATE copilot_execution_receipts "
                "SET status='completed', outcome=?, completed_at=? "
                "WHERE store_id=? AND action_id=? AND idempotency_key=? AND status='pending'",
                (
                    json.dumps(outcome, ensure_ascii=False), now_iso,
                    store_id, action_id, idempotency_key,
                ),
            )
            if receipt_update.rowcount != 1:
                raise RuntimeError("internal_execution_receipt_update_failed")
            cx.execute("COMMIT")
            return True
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
            "SELECT username, role, nv_id, display_name, email FROM users ORDER BY username"
        ).fetchall()
    return [
        {
            "username": str(r[0]),
            "role": str(r[1]),
            "nv_id": str(r[2]),
            "display_name": str(r[3]),
            "email": str(r[4] or ""),
        }
        for r in rows
    ]


def set_user_email(username: str, email: str) -> dict[str, str]:
    """Nick cập nhật gmail của chính mình (hoặc quản lý cập nhật cho NV)."""
    u = (username or "").strip().lower()
    em = (email or "").strip()
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT username FROM users WHERE username=?", (u,)
        ).fetchone()
        if not row:
            raise DangKyLoi("khong_co_tai_khoan")
        cx.execute("UPDATE users SET email=? WHERE username=?", (em, u))
        return {"username": u, "email": em}


def get_user_emails() -> dict[str, str]:
    """Trả map nv_id -> email (đã set). Dùng cho AI gửi mail."""
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            "SELECT nv_id, email FROM users WHERE email != ''"
        ).fetchall()
    return {str(r[0]): str(r[1]) for r in rows}


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


def ha_vai(username: str) -> dict[str, str]:
    """Chủ quán hạ quản lý xuống nhân viên."""
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
        if row[1] != "quan_ly":
            raise NangVaiLoi("vai_khong_hop_le")
        cx.execute("UPDATE users SET role=? WHERE username=?", ("nhan_vien", u))
        cx.execute("UPDATE sessions SET role=? WHERE username=?", ("nhan_vien", u))
        return {
            "username": str(row[0]),
            "role": "nhan_vien",
            "nv_id": str(row[2]),
            "display_name": str(row[3]),
        }


def _menu_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "ten": str(row[1]),
        "gia": int(row[2]),
        "an": bool(row[3]),
        "bom": json.loads(row[4]) if row[4] else {},
        "hinh_url": str(row[5]) if len(row) > 5 and row[5] else "",
    }


def menu_list(*, gom_an: bool = False) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            "SELECT id, ten, gia, an, bom, hinh_url FROM menu_mon ORDER BY ten"
        ).fetchall()
    out = []
    for row in rows:
        if not gom_an and int(row[3]):
            continue
        out.append(_menu_from_row(row))
    return out


def menu_upsert(mon: dict[str, Any]) -> dict[str, Any]:
    init_db()
    mid = str(mon["id"]).strip()
    ten = str(mon["ten"]).strip()
    gia = int(mon["gia"])
    an = 1 if mon.get("an") else 0
    hinh_url = str(mon.get("hinh_url") or "").strip()
    bom = json.dumps(mon.get("bom") or {}, ensure_ascii=False)
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO menu_mon(id, ten, gia, an, bom, hinh_url) VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET ten=excluded.ten, gia=excluded.gia,
                an=excluded.an, bom=excluded.bom, hinh_url=excluded.hinh_url
            """,
            (mid, ten, gia, an, bom, hinh_url),
        )
    return _menu_from_row((mid, ten, gia, an, bom, hinh_url))


def menu_get(mon_id: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT id, ten, gia, an, bom, hinh_url FROM menu_mon WHERE id=?", (mon_id,)
        ).fetchone()
    if not row:
        return None
    return _menu_from_row(row)


def menu_set_hinh(mon_id: str, hinh_url: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT id, ten, gia, an, bom, hinh_url FROM menu_mon WHERE id=?", (mon_id,)
        ).fetchone()
        if not row:
            return None
        cx.execute("UPDATE menu_mon SET hinh_url=? WHERE id=?", (hinh_url, mon_id))
    return _menu_from_row((*row[:5], hinh_url))


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


# ── Copilot Drafts & Audit ───────────────────────────────────────────────────

def copilot_draft_save(draft: dict[str, Any]) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO copilot_draft_actions(
                action_id, intent, status, store_id, created_by, confidence,
                summary, explanation, payload_diff, requires_confirmation,
                data_snapshot_hash, expires_at, created_at, executed_at,
                amended_from, amended_by
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(action_id) DO UPDATE SET
                status=excluded.status,
                summary=excluded.summary,
                explanation=excluded.explanation,
                payload_diff=excluded.payload_diff,
                data_snapshot_hash=excluded.data_snapshot_hash,
                expires_at=excluded.expires_at,
                executed_at=excluded.executed_at,
                amended_from=excluded.amended_from,
                amended_by=excluded.amended_by
            """,
            (
                draft["action_id"],
                draft["intent"],
                draft.get("status", "draft"),
                draft.get("store_id", "quan_01"),
                draft.get("created_by", "system"),
                float(draft.get("confidence", 1.0)),
                draft.get("summary", ""),
                draft.get("explanation", ""),
                json.dumps(draft.get("payload_diff", {}), ensure_ascii=False),
                1 if draft.get("requires_confirmation", True) else 0,
                draft.get("data_snapshot_hash", ""),
                draft.get("expires_at", ""),
                draft.get("created_at", ""),
                draft.get("executed_at"),
                draft.get("amended_from"),
                draft.get("amended_by"),
            ),
        )


def copilot_draft_get(action_id: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT action_id, intent, status, store_id, created_by, confidence,
                   summary, explanation, payload_diff, requires_confirmation,
                   data_snapshot_hash, expires_at, created_at, executed_at,
                   amended_from, amended_by
            FROM copilot_draft_actions WHERE action_id=?
            """,
            (action_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "action_id": str(row[0]),
            "intent": str(row[1]),
            "status": str(row[2]),
            "store_id": str(row[3]),
            "created_by": str(row[4]),
            "confidence": float(row[5]),
            "summary": str(row[6]),
            "explanation": str(row[7]),
            "payload_diff": json.loads(row[8]),
            "requires_confirmation": bool(row[9]),
            "data_snapshot_hash": str(row[10]),
            "expires_at": str(row[11]),
            "created_at": str(row[12]),
            "executed_at": str(row[13]) if row[13] else None,
            "amended_from": str(row[14]) if row[14] else None,
            "amended_by": str(row[15]) if row[15] else None,
        }


def copilot_draft_update_status(
    action_id: str,
    status: str,
    executed_at: str | None = None,
    amended_from: str | None = None,
    amended_by: str | None = None,
) -> bool:
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            """
            UPDATE copilot_draft_actions
            SET status=?, executed_at=?, amended_from=?, amended_by=?
            WHERE action_id=?
            """,
            (status, executed_at, amended_from, amended_by, action_id),
        )
        return cur.rowcount > 0


def copilot_draft_compare_and_set_status(
    action_id: str,
    expected_status: str,
    new_status: str,
) -> bool:
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            """
            UPDATE copilot_draft_actions
            SET status=?
            WHERE action_id=? AND status=?
            """,
            (new_status, action_id, expected_status),
        )
        return cur.rowcount == 1


def copilot_execution_reserve(
    store_id: str,
    action_id: str,
    idempotency_key: str,
    request_hash: str,
) -> tuple[str, dict[str, Any] | None]:
    init_db()
    with _conn() as cx:
        try:
            cx.execute(
                """
                INSERT INTO copilot_execution_receipts(
                    store_id, action_id, idempotency_key, request_hash, status, created_at
                ) VALUES (?,?,?,?,?,?)
                """,
                (store_id, action_id, idempotency_key, request_hash, "pending", _iso_now()),
            )
            return "reserved", None
        except sqlite3.IntegrityError:
            row = cx.execute(
                """
                SELECT idempotency_key, request_hash, status, outcome
                FROM copilot_execution_receipts
                WHERE store_id=? AND action_id=?
                """,
                (store_id, action_id),
            ).fetchone()
            if not row or str(row[0]) != idempotency_key or str(row[1]) != request_hash:
                return "conflict", None
            if str(row[2]) == "completed" and row[3]:
                return "replay", json.loads(row[3])
            return "pending", None


def copilot_execution_rearm_internal(
    store_id: str,
    action_id: str,
    idempotency_key: str,
    request_hash: str,
) -> bool:
    """Re-arm a failed KV-only execution after its transaction rolled back."""
    init_db()
    with _conn() as cx:
        cx.isolation_level = None
        cx.execute("BEGIN IMMEDIATE")
        try:
            row = cx.execute(
                "SELECT status FROM copilot_execution_receipts "
                "WHERE store_id=? AND action_id=?",
                (store_id, action_id),
            ).fetchone()
            if not row or str(row[0]) != "failed":
                cx.execute("ROLLBACK")
                return False
            action = cx.execute(
                "UPDATE copilot_draft_actions SET status='ready_for_approval', executed_at=NULL "
                "WHERE action_id=? AND store_id=? AND status='execution_failed'",
                (action_id, store_id),
            )
            if action.rowcount != 1:
                cx.execute("ROLLBACK")
                return False
            receipt = cx.execute(
                "DELETE FROM copilot_execution_receipts "
                "WHERE store_id=? AND action_id=? AND status='failed'",
                (store_id, action_id),
            )
            if receipt.rowcount != 1:
                cx.execute("ROLLBACK")
                return False
            cx.execute("COMMIT")
            return True
        except Exception:
            cx.execute("ROLLBACK")
            raise


def copilot_execution_complete(
    store_id: str,
    action_id: str,
    idempotency_key: str,
    outcome: dict[str, Any],
) -> bool:
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            """
            UPDATE copilot_execution_receipts
            SET status='completed', outcome=?, completed_at=?
            WHERE store_id=? AND action_id=? AND idempotency_key=? AND status='pending'
            """,
            (
                json.dumps(outcome, ensure_ascii=False),
                _iso_now(),
                store_id,
                action_id,
                idempotency_key,
            ),
        )
        return cur.rowcount == 1


def copilot_execution_fail(
    store_id: str,
    action_id: str,
    idempotency_key: str,
    error_type: str,
) -> bool:
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            """
            UPDATE copilot_execution_receipts
            SET status='failed', outcome=?, completed_at=?
            WHERE store_id=? AND action_id=? AND idempotency_key=? AND status='pending'
            """,
            (
                json.dumps({"error_type": error_type}, ensure_ascii=False),
                _iso_now(),
                store_id,
                action_id,
                idempotency_key,
            ),
        )
        return cur.rowcount == 1


def copilot_mail_delivery_reserve(
    store_id: str,
    idempotency_key: str,
    request_hash: str,
) -> tuple[str, dict[str, Any] | None]:
    """Reserve one external mail request and replay a known terminal outcome."""
    init_db()
    with _conn() as cx:
        try:
            cx.execute(
                "INSERT INTO copilot_mail_delivery_receipts(" 
                "store_id, idempotency_key, request_hash, status, created_at) "
                "VALUES (?,?,?,?,?)",
                (store_id, idempotency_key, request_hash, "pending", _iso_now()),
            )
            return "reserved", None
        except sqlite3.IntegrityError:
            row = cx.execute(
                "SELECT request_hash, status, outcome "
                "FROM copilot_mail_delivery_receipts WHERE store_id=? AND idempotency_key=?",
                (store_id, idempotency_key),
            ).fetchone()
            if not row or str(row[0]) != request_hash:
                return "conflict", None
            if str(row[1]) in {"sent", "transport_failed", "delivery_unknown"} and row[2]:
                return "replay", json.loads(row[2])
            return "pending", None


def copilot_mail_delivery_complete(
    store_id: str,
    idempotency_key: str,
    status: str,
    outcome: dict[str, Any],
) -> bool:
    if status not in {"sent", "transport_failed", "delivery_unknown"}:
        raise ValueError("invalid_mail_delivery_status")
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            "UPDATE copilot_mail_delivery_receipts SET status=?, outcome=?, completed_at=? "
            "WHERE store_id=? AND idempotency_key=? AND status='pending'",
            (
                status, json.dumps(outcome, ensure_ascii=False), _iso_now(),
                store_id, idempotency_key,
            ),
        )
        return cur.rowcount == 1


def copilot_draft_list(
    store_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    init_db()
    query = """
        SELECT action_id, intent, status, store_id, created_by, confidence,
               summary, explanation, payload_diff, requires_confirmation,
               data_snapshot_hash, expires_at, created_at, executed_at,
               amended_from, amended_by
        FROM copilot_draft_actions
    """
    params: list[Any] = []
    conds = []
    if store_id:
        conds.append("store_id=?")
        params.append(store_id)
    if status:
        conds.append("status=?")
        params.append(status)
    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with _conn() as cx:
        rows = cx.execute(query, params).fetchall()
        return [
            {
                "action_id": str(r[0]),
                "intent": str(r[1]),
                "status": str(r[2]),
                "store_id": str(r[3]),
                "created_by": str(r[4]),
                "confidence": float(r[5]),
                "summary": str(r[6]),
                "explanation": str(r[7]),
                "payload_diff": json.loads(r[8]),
                "requires_confirmation": bool(r[9]),
                "data_snapshot_hash": str(r[10]),
                "expires_at": str(r[11]),
                "created_at": str(r[12]),
                "executed_at": str(r[13]) if r[13] else None,
                "amended_from": str(r[14]) if r[14] else None,
                "amended_by": str(r[15]) if r[15] else None,
            }
            for r in rows
        ]


def copilot_audit_add(
    action_id: str,
    actor_user_id: str,
    store_id: str,
    intent: str,
    decision: str,
    payload_diff: dict[str, Any] | None = None,
    channel: str = "web",
    latency_ms: int = 0,
) -> None:
    try:
        from datetime import UTC, datetime
    except ImportError:
        from datetime import datetime, timezone
        UTC = timezone.utc

    init_db()
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO copilot_audit_log(
                action_id, actor_user_id, store_id, intent, decision,
                payload_diff, timestamp, channel, latency_ms
            )
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                action_id,
                actor_user_id,
                store_id,
                intent,
                decision,
                json.dumps(payload_diff or {}, ensure_ascii=False),
                now_iso,
                channel,
                latency_ms,
            ),
        )


def copilot_audit_list(store_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT action_id, actor_user_id, store_id, intent, decision, payload_diff, timestamp, channel, latency_ms FROM copilot_audit_log"
    params: list[Any] = []
    if store_id:
        query += " WHERE store_id=?"
        params.append(store_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _conn() as cx:
        rows = cx.execute(query, params).fetchall()
        return [
            {
                "action_id": str(r[0]),
                "actor_user_id": str(r[1]),
                "store_id": str(r[2]),
                "intent": str(r[3]),
                "decision": str(r[4]),
                "payload_diff": json.loads(r[5]),
                "timestamp": str(r[6]),
                "channel": str(r[7]),
                "latency_ms": int(r[8]),
            }
            for r in rows
        ]


# ── FB moderation store (kế hoạch chatbot §3.7) ───────────────────────────


def _iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fb_try_claim_event(event_id: str) -> bool:
    """True nếu lần đầu thấy event_id (mid/comment_id); False nếu đã xử lý.

    Idempotency chống webhook retry của Meta (kế hoạch §6.2b).
    """
    init_db()
    with _conn() as cx:
        try:
            cx.execute(
                "INSERT INTO fb_processed_events(event_id, processed_at) VALUES (?,?)",
                (event_id, _iso_now()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def fb_try_claim_scoped_event(*, store_id: str, page_id: str, event_type: str, external_event_id: str) -> bool:
    """Atomically claim one Facebook event in its tenant/Page/type scope."""
    if not all(value.strip() for value in (store_id, page_id, event_type, external_event_id)):
        return False
    idempotency_key = hashlib.sha256(f"{store_id}:{page_id}:{event_type}:{external_event_id}".encode()).hexdigest()
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            "INSERT INTO fb_event_receipts(idempotency_key, store_id, page_id, event_type, external_event_id, processed_at) VALUES (?,?,?,?,?,?) ON CONFLICT(idempotency_key) DO NOTHING",
            (idempotency_key, store_id, page_id, event_type, external_event_id, _iso_now()),
        )
        return cur.rowcount == 1


_AI_LEARNING_TABLES = {"generation": "ai_generation_records", "feedback": "ai_feedback_events", "evaluation": "ai_evaluations", "rule_proposal": "ai_rule_proposals"}


def _ai_generation_exists(cx: sqlite3.Connection, *, store_id: str, generation_id: str) -> bool:
    return cx.execute("SELECT 1 FROM ai_generation_records WHERE store_id=? AND id=?", (store_id, generation_id)).fetchone() is not None


def ai_learning_save(kind: str, record: dict[str, Any]) -> bool:
    """Persist a pre-redacted AI-learning record; return False for idempotent replay."""
    if kind not in _AI_LEARNING_TABLES:
        raise ValueError("ai_learning_record_invalid")
    try:
        store_id, record_id, channel, created_at = (str(record[key]).strip() for key in ("store_id", "id", "channel", "created_at"))
    except (KeyError, TypeError):
        raise ValueError("ai_learning_record_invalid") from None
    if not all((store_id, record_id, channel, created_at)):
        raise ValueError("ai_learning_record_invalid")
    payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    init_db()
    with _conn() as cx:
        if kind == "generation":
            cur = cx.execute("INSERT INTO ai_generation_records(id, store_id, channel, idempotency_key, payload, created_at) VALUES (?,?,?,?,?,?) ON CONFLICT(store_id, idempotency_key) DO NOTHING", (record_id, store_id, channel, str(record["idempotency_key"]), payload, created_at))
        elif kind == "feedback":
            if not _ai_generation_exists(cx, store_id=store_id, generation_id=str(record["generation_id"])):
                raise ValueError("ai_learning_cross_tenant_generation")
            cur = cx.execute("INSERT INTO ai_feedback_events(id, store_id, generation_id, channel, idempotency_key, payload, created_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(store_id, idempotency_key) DO NOTHING", (record_id, store_id, str(record["generation_id"]), channel, str(record["idempotency_key"]), payload, created_at))
        elif kind == "evaluation":
            if not _ai_generation_exists(cx, store_id=store_id, generation_id=str(record["generation_id"])):
                raise ValueError("ai_learning_cross_tenant_generation")
            cur = cx.execute("INSERT INTO ai_evaluations(id, store_id, generation_id, channel, idempotency_key, payload, created_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(store_id, idempotency_key) DO NOTHING", (record_id, store_id, str(record["generation_id"]), channel, str(record["idempotency_key"]), payload, created_at))
        else:
            evidence_ids = [str(value) for value in record.get("evidence_ids", [])]
            if not evidence_ids:
                raise ValueError("ai_learning_evidence_missing")
            placeholders = ",".join("?" for _ in evidence_ids)
            rows = cx.execute(f"SELECT id FROM ai_feedback_events WHERE store_id=? AND id IN ({placeholders})", [store_id, *evidence_ids]).fetchall()
            if {str(row[0]) for row in rows} != set(evidence_ids):
                raise ValueError("ai_learning_cross_tenant_evidence")
            cur = cx.execute("INSERT INTO ai_rule_proposals(id, store_id, channel, status, version, idempotency_key, payload, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(store_id, idempotency_key) DO NOTHING", (record_id, store_id, channel, str(record.get("status", "pending")), int(record["version"]), str(record["idempotency_key"]), payload, created_at, str(record["updated_at"])))
        return cur.rowcount == 1


def ai_learning_list(kind: str, *, store_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Read AI-learning records only from the requested tenant."""
    if kind not in _AI_LEARNING_TABLES or not store_id.strip():
        raise ValueError("ai_learning_query_invalid")
    init_db()
    with _conn() as cx:
        rows = cx.execute(f"SELECT payload FROM {_AI_LEARNING_TABLES[kind]} WHERE store_id=? ORDER BY created_at DESC LIMIT ?", (store_id, max(1, min(limit, 200)))).fetchall()
    return [json.loads(str(row[0])) for row in rows]


_AI_RULE_TRANSITIONS = {
    "pending": {"approved", "rejected", "conflict_pending"},
    "conflict_pending": {"approved", "rejected"},
    "approved": {"active", "rejected"},
    "active": {"paused", "rolled_back"},
    "paused": {"active", "rolled_back"},
}


def ai_rule_proposal_get(*, store_id: str, proposal_id: str) -> dict[str, Any] | None:
    """Return one proposal only when it belongs to the requested tenant."""
    if not store_id.strip() or not proposal_id.strip():
        raise ValueError("ai_learning_query_invalid")
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT payload FROM ai_rule_proposals WHERE store_id=? AND id=?",
            (store_id, proposal_id),
        ).fetchone()
    return json.loads(str(row[0])) if row else None


def ai_rule_proposal_list(
    *, store_id: str, channel: str | None = None, status: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    """List proposal records scoped to one tenant, optionally by channel/status."""
    if not store_id.strip():
        raise ValueError("ai_learning_query_invalid")
    init_db()
    query = "SELECT payload FROM ai_rule_proposals WHERE store_id=?"
    params: list[Any] = [store_id]
    if channel:
        query += " AND channel=?"
        params.append(channel)
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(max(1, min(limit, 200)))
    with _conn() as cx:
        rows = cx.execute(query, params).fetchall()
    return [json.loads(str(row[0])) for row in rows]


def ai_rule_proposal_transition(
    *, store_id: str, proposal_id: str, target_status: str, actor_id: str, updated_at: str,
    rejection_reason: str | None = None,
) -> dict[str, Any] | None:
    """Atomically apply a legal, tenant-scoped human rule lifecycle transition."""
    if not all(value.strip() for value in (store_id, proposal_id, target_status, actor_id, updated_at)):
        raise ValueError("ai_learning_transition_invalid")
    init_db()
    with _conn() as cx:
        row = cx.execute(
            "SELECT status, payload FROM ai_rule_proposals WHERE store_id=? AND id=?",
            (store_id, proposal_id),
        ).fetchone()
        if not row:
            return None
        current_status = str(row[0])
        if target_status not in _AI_RULE_TRANSITIONS.get(current_status, set()):
            raise ValueError("ai_learning_transition_invalid")
        proposal = json.loads(str(row[1]))
        proposal["status"] = target_status
        proposal["updated_at"] = updated_at
        if target_status in {"approved", "active"}:
            proposal["approved_by"] = actor_id
            proposal["approved_at"] = updated_at
            proposal["rejection_reason"] = None
        elif target_status == "rejected":
            proposal["rejection_reason"] = (rejection_reason or "rejected_by_owner").strip()
        payload = json.dumps(proposal, ensure_ascii=False, separators=(",", ":"))
        cur = cx.execute(
            "UPDATE ai_rule_proposals SET status=?, payload=?, updated_at=? WHERE store_id=? AND id=? AND status=?",
            (target_status, payload, updated_at, store_id, proposal_id, current_status),
        )
        return proposal if cur.rowcount == 1 else None


def ai_rule_active_list(*, store_id: str, channel: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return active rules ordered deterministically for prompt construction."""
    rules = ai_rule_proposal_list(store_id=store_id, channel=channel, status="active", limit=limit)
    return sorted(
        rules,
        key=lambda rule: (-int((rule.get("rule") or {}).get("priority", 0)), str(rule.get("created_at", "")), str(rule.get("id", ""))),
    )


def ai_learning_snapshot(*, store_id: str) -> dict[str, Any]:
    """Return a consistent per-store export and SHA-256 manifest for backup tooling."""
    if not store_id.strip():
        raise ValueError("ai_learning_query_invalid")
    init_db()
    with _conn() as cx:
        cx.isolation_level = None
        cx.execute("BEGIN")
        try:
            records = {kind: [json.loads(str(row[0])) for row in cx.execute(f"SELECT payload FROM {table} WHERE store_id=? ORDER BY created_at, id", (store_id,)).fetchall()] for kind, table in _AI_LEARNING_TABLES.items()}
            cx.execute("COMMIT")
        except Exception:
            cx.execute("ROLLBACK")
            raise
    snapshot = {"schema_version": 1, "store_id": store_id, "records": records}
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"snapshot": snapshot, "checksum_sha256": hashlib.sha256(payload).hexdigest()}


def ai_learning_backup(*, store_id: str, directory: Path | None = None) -> dict[str, Any]:
    """Write a tenant-scoped consistent snapshot plus checksum manifest atomically."""
    from ca_api.ai_learning.security import require_encrypted_data_path

    backup = ai_learning_snapshot(store_id=store_id)
    output_dir = directory or Path(os.environ.get("NHIPQUAN_AI_LEARNING_BACKUP_DIR", ROOT / "data" / "backups"))
    require_encrypted_data_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_store = re.sub(r"[^A-Za-z0-9_.-]", "_", store_id)
    snapshot_path = output_dir / f"ai-learning-{safe_store}-{stamp}.json"
    manifest_path = snapshot_path.with_suffix(".sha256.json")
    snapshot_payload = json.dumps(backup["snapshot"], ensure_ascii=False, sort_keys=True, indent=2)
    manifest = {
        "backup_format_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "schema_version": backup["snapshot"]["schema_version"],
        "store_id": store_id,
        "store_coverage": [store_id],
        "record_counts": {kind: len(records) for kind, records in backup["snapshot"]["records"].items()},
        "checksum_sha256": backup["checksum_sha256"],
        "snapshot_file": snapshot_path.name,
    }
    for path, content in ((snapshot_path, snapshot_payload), (manifest_path, json.dumps(manifest, indent=2, sort_keys=True))):
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    return {**backup, "snapshot_path": str(snapshot_path), "manifest_path": str(manifest_path)}


def ai_learning_verify_backup(*, snapshot_path: Path, manifest_path: Path) -> bool:
    """Verify backup format, manifest coverage, and SHA-256 before a restore."""
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return bool(
        manifest.get("backup_format_version") == 1
        and manifest.get("schema_version") == snapshot.get("schema_version") == 1
        and manifest.get("store_coverage") == [snapshot.get("store_id")]
        and manifest.get("checksum_sha256") == digest
    )


def fb_review_insert(item: dict[str, Any]) -> int:
    """Ghi 1 hàng vào fb_review_queue, trả về id."""
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            """
            INSERT INTO fb_review_queue(
                source, external_thread_id, external_psid, external_user_name,
                post_id, post_is_sensitive, message_text, detected_intent,
                confidence, policy_action, assigned_role, proposed_response,
                flagged_reasons, status, trace_id, created_at, expires_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item["source"],
                item["external_thread_id"],
                item["external_psid"],
                item.get("external_user_name"),
                item.get("post_id"),
                1 if item.get("post_is_sensitive") else 0,
                item["message_text"],
                item["detected_intent"],
                float(item["confidence"]),
                item["policy_action"],
                item.get("assigned_role"),
                item.get("proposed_response"),
                json.dumps(item.get("flagged_reasons") or [], ensure_ascii=False),
                item.get("status", "pending"),
                item.get("trace_id", ""),
                item["created_at"],
                item.get("expires_at"),
            ),
        )
        return int(cur.lastrowid or 0)


def fb_review_list(
    *,
    status: str | None = None,
    assigned_role: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    init_db()
    q = "SELECT * FROM fb_review_queue WHERE 1=1"
    params: list[Any] = []
    if status:
        q += " AND status=?"
        params.append(status)
    if assigned_role:
        q += " AND assigned_role=?"
        params.append(assigned_role)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, min(int(limit), 200)))
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def fb_review_get(item_id: int) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        row = cx.execute(
            "SELECT * FROM fb_review_queue WHERE id=?", (item_id,)
        ).fetchone()
    return dict(row) if row else None


def fb_review_link_generation(item_id: int, *, generation_id: str) -> None:
    """Attach the exact AI generation that produced this review draft."""
    init_db()
    with _conn() as cx:
        cx.execute(
            "UPDATE fb_review_queue SET ai_generation_id=? WHERE id=?",
            (generation_id, item_id),
        )


def fb_review_decide(
    item_id: int,
    *,
    status: str,
    decided_by: str,
    final_response: str | None = None,
) -> dict[str, Any] | None:
    """Cập nhật quyết định duyệt/từ chối. Idempotent: đã quyết thì không đổi."""
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        row = cx.execute(
            "SELECT status FROM fb_review_queue WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            return None
        if str(row["status"]) != "pending":
            return dict(row)
        cx.execute(
            "UPDATE fb_review_queue SET status=?, decided_by=?, decided_at=?, final_response=? "
            "WHERE id=? AND status='pending'",
            (status, decided_by, _iso_now(), final_response, item_id),
        )
        row2 = cx.execute(
            "SELECT * FROM fb_review_queue WHERE id=?", (item_id,)
        ).fetchone()
    return dict(row2) if row2 else None


def fb_review_mark_sent(item_id: int, *, final_response: str, audit_id: int) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "UPDATE fb_review_queue SET status='sent', final_response=?, audit_sent=? WHERE id=?",
            (final_response, audit_id, item_id),
        )


def fb_escalation_add(
    review_queue_id: int, *, escalated_to: str, reason: str, notified_channel: str
) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "INSERT INTO fb_escalation_log(review_queue_id, escalated_to, reason, notified_channel, notified_at) "
            "VALUES (?,?,?,?,?)",
            (review_queue_id, escalated_to, reason, notified_channel, _iso_now()),
        )


def fb_escalation_unacked() -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT e.*, q.message_text, q.detected_intent FROM fb_escalation_log e "
            "JOIN fb_review_queue q ON q.id = e.review_queue_id "
            "WHERE e.acked_at IS NULL ORDER BY e.notified_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def fb_blacklist_check(psid: str) -> bool:
    """True nếu PSID đang bị chặn (blocked_until > now)."""
    init_db()
    now = _iso_now()
    with _conn() as cx:
        row = cx.execute(
            "SELECT blocked_until FROM fb_psid_blacklist WHERE psid=?", (psid,)
        ).fetchone()
    return bool(row and str(row[0]) > now)


def fb_blacklist_bump(psid: str, *, strikes: int, blocked_until: str, reason: str) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "INSERT INTO fb_psid_blacklist(psid, strikes, blocked_until, reason) VALUES (?,?,?,?) "
            "ON CONFLICT(psid) DO UPDATE SET strikes=excluded.strikes, "
            "blocked_until=excluded.blocked_until, reason=excluded.reason",
            (psid, strikes, blocked_until, reason),
        )


def fb_stats() -> dict[str, Any]:
    """Đếm theo status + auto rate (kế hoạch §5.4)."""
    init_db()
    with _conn() as cx:
        by_status = {
            str(r[0]): int(r[1])
            for r in cx.execute(
                "SELECT status, COUNT(*) FROM fb_review_queue GROUP BY status"
            ).fetchall()
        }
        total = sum(by_status.values())
    auto = by_status.get("auto_sent", 0)
    return {
        "by_status": by_status,
        "total": total,
        "auto_sent": auto,
        "auto_rate": round(auto / total, 4) if total else 0.0,
        "escalation_unacked": len(fb_escalation_unacked()),
    }


# ── Chat Nội Bộ Nhân Viên (Messenger-Style) ──────────────────────────────────

def _seed_chat_neu_trong(cx: sqlite3.Connection) -> None:
    """Tạo phòng chat chung mặc định '☕ NHỊP QUÁN · Hội Quán Chung' (is_locked=1) và mời toàn bộ nhân viên active."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conv_id = f"conv_general_{DEFAULT_STORE_ID}"
    cx.execute(
        """
        INSERT OR IGNORE INTO chat_conversations(id, store_id, type, display_name, avatar_url, is_locked, created_at, updated_at)
        VALUES (?,?,?,?,?,1,?,?)
        """,
        (conv_id, DEFAULT_STORE_ID, "general", "☕ NHỊP QUÁN · Hội Quán Chung", "", now, now),
    )
    users = cx.execute("SELECT nv_id, role, status FROM users WHERE store_id=?", (DEFAULT_STORE_ID,)).fetchall()
    for nv, role, st in users:
        if st == "inactive":
            continue
        part_role = "admin" if role in ("quan_ly", "chu_quan") else "member"
        cx.execute(
            """
            INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
            VALUES (?,?,?,?,?)
            """,
            (conv_id, nv, part_role, "active", now),
        )
    has_msg = cx.execute("SELECT 1 FROM chat_messages WHERE conversation_id=? LIMIT 1", (conv_id,)).fetchone()
    if not has_msg:
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        cx.execute(
            """
            INSERT OR IGNORE INTO chat_messages(id, conversation_id, sender_id, type, content, is_unsent, created_at)
            VALUES (?,?,'system','system',?,0,?)
            """,
            (
                msg_id,
                conv_id,
                "Chào mừng cả nhà đến với kênh Chat Hội Quán NHỊP QUÁN! ☕✨ Trao đổi ca làm việc, hỗ trợ quầy, pha chế và thông báo tại đây nhé.",
                now,
            ),
        )


def user_is_active(nv_id: str) -> bool:
    """Kiểm tra tài khoản nhân viên có đang hoạt động (active) hay không."""
    init_db()
    with _conn() as cx:
        row = cx.execute("SELECT status FROM users WHERE nv_id=?", (nv_id,)).fetchone()
        if not row:
            return False
        return str(row[0]).lower() == "active"


def chat_participant_deactivate(nv_id: str) -> None:
    """Hook Offboarding: Đưa thành viên vào trạng thái 'archived' trên mọi hội thoại."""
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            UPDATE chat_participants
            SET status = 'archived', archived_at = ?
            WHERE nv_id = ? AND status = 'active'
            """,
            (now, nv_id),
        )


def user_deactivate(nv_id: str, store_id: str = "quan_01") -> bool:
    """Vô hiệu hóa tài khoản nhân viên (Offboarding):
    - Đổi status = 'inactive' trong bảng users
    - Xóa toàn bộ token trong sessions (force revoke/disconnect)
    - Set status = 'archived' trong chat_participants
    - Ghi log audit
    """
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        user = cx.execute("SELECT username, display_name FROM users WHERE nv_id=?", (nv_id,)).fetchone()
        if not user:
            return False
        u_name, d_name = str(user[0]), str(user[1])
        cx.execute("UPDATE users SET status = 'inactive' WHERE nv_id = ?", (nv_id,))
        cx.execute("DELETE FROM sessions WHERE nv_id = ?", (nv_id,))
        cx.execute(
            """
            UPDATE chat_participants
            SET status = 'archived', archived_at = ?
            WHERE nv_id = ?
            """,
            (now, nv_id),
        )
        cx.execute(
            "INSERT INTO audit(at, ai, hanh, payload) VALUES (?,?,?,?)",
            (now, "system", "user_deactivate", json.dumps({"nv_id": nv_id, "username": u_name, "name": d_name})),
        )
    return True


def chat_conversation_create(
    store_id: str,
    conv_type: str,
    display_name: str,
    created_by: str,
    participant_nv_ids: list[str],
    is_locked: bool = False,
    avatar_url: str = "",
) -> dict[str, Any]:
    init_db()
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO chat_conversations(id, store_id, type, display_name, avatar_url, is_locked, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (conv_id, store_id, conv_type, display_name, avatar_url, 1 if is_locked else 0, now, now),
        )
        all_participants = set(participant_nv_ids)
        if created_by:
            all_participants.add(created_by)
        for nv in all_participants:
            role = "admin" if nv == created_by else "member"
            cx.execute(
                """
                INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
                VALUES (?,?,?,?,?)
                """,
                (conv_id, nv, role, "active", now),
            )
    return chat_conversation_get(conv_id, created_by) or {"id": conv_id}


def chat_get_or_create_direct(store_id: str, nv1_id: str, nv2_id: str) -> dict[str, Any]:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT c.id FROM chat_conversations c
            JOIN chat_participants p1 ON c.id = p1.conversation_id AND p1.nv_id = ?
            JOIN chat_participants p2 ON c.id = p2.conversation_id AND p2.nv_id = ?
            WHERE c.type = 'direct' AND c.store_id = ?
            LIMIT 1
            """,
            (nv1_id, nv2_id, store_id),
        ).fetchone()
        if row:
            conv_id = str(row[0])
            return chat_conversation_get(conv_id, nv1_id) or {"id": conv_id}

    return chat_conversation_create(
        store_id=store_id,
        conv_type="direct",
        display_name="",
        created_by=nv1_id,
        participant_nv_ids=[nv1_id, nv2_id],
    )


def chat_conversation_get(conv_id: str, current_nv_id: str | None = None) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT id, store_id, type, display_name, avatar_url, is_locked, created_at, updated_at
            FROM chat_conversations WHERE id = ?
            """,
            (conv_id,),
        ).fetchone()
        if not row:
            return None
        conv: dict[str, Any] = {
            "id": str(row[0]),
            "store_id": str(row[1]),
            "type": str(row[2]),
            "display_name": str(row[3]),
            "avatar_url": str(row[4] or ""),
            "is_locked": bool(row[5]),
            "created_at": str(row[6]),
            "updated_at": str(row[7]),
        }
        # Lấy thành viên
        p_rows = cx.execute(
            """
            SELECT p.nv_id, p.role, p.status, p.muted, p.last_read_at, p.joined_at, p.archived_at,
                   COALESCE(u.display_name, p.nv_id) as user_name,
                   COALESCE(u.role, 'nhan_vien') as user_role,
                   COALESCE(u.status, 'active') as user_status
            FROM chat_participants p
            LEFT JOIN users u ON p.nv_id = u.nv_id
            WHERE p.conversation_id = ?
            """,
            (conv_id,),
        ).fetchall()
        conv["participants"] = [
            {
                "nv_id": str(r[0]),
                "role": str(r[1]),
                "status": str(r[2]),
                "muted": bool(r[3]),
                "last_read_at": str(r[4] or ""),
                "joined_at": str(r[5]),
                "archived_at": str(r[6] or ""),
                "display_name": str(r[7]),
                "user_role": str(r[8]),
                "user_status": str(r[9]),
            }
            for r in p_rows
        ]

        if conv["type"] == "direct" and current_nv_id:
            other = next((p for p in conv["participants"] if p["nv_id"] != current_nv_id), None)
            if other:
                conv["display_name"] = other["display_name"]
                conv["other_user"] = other

        # Tin nhắn cuối
        last_msg_row = cx.execute(
            """
            SELECT m.id, m.sender_id, m.type, m.content, m.created_at, m.is_unsent,
                   COALESCE(u.display_name, m.sender_id) as sender_name
            FROM chat_messages m
            LEFT JOIN users u ON m.sender_id = u.nv_id
            WHERE m.conversation_id = ?
            ORDER BY m.created_at DESC LIMIT 1
            """,
            (conv_id,),
        ).fetchone()
        if last_msg_row:
            conv["last_message"] = {
                "id": str(last_msg_row[0]),
                "sender_id": str(last_msg_row[1]),
                "type": str(last_msg_row[2]),
                "content": str(last_msg_row[3]),
                "created_at": str(last_msg_row[4]),
                "is_unsent": bool(last_msg_row[5]),
                "sender_name": str(last_msg_row[6]),
            }
        else:
            conv["last_message"] = None

        return conv


def chat_conversation_list_for_user(nv_id: str, store_id: str = "quan_01") -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        # Nếu user bị inactive, không trả về hộp thư
        u_row = cx.execute("SELECT status FROM users WHERE nv_id = ?", (nv_id,)).fetchone()
        if not u_row or str(u_row[0]) == "inactive":
            return []

        # Đảm bảo user luôn có mặt trong nhóm chung của quán
        conv_general_id = f"conv_general_{store_id}"
        now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        cx.execute(
            """
            INSERT OR IGNORE INTO chat_conversations(id, store_id, type, display_name, avatar_url, is_locked, created_at, updated_at)
            VALUES (?,?,?,?,?,1,?,?)
            """,
            (conv_general_id, store_id, "general", "☕ NHỊP QUÁN · Hội Quán Chung", "", now_iso, now_iso),
        )
        cx.execute(
            """
            INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
            VALUES (?,?,'member','active',?)
            """,
            (conv_general_id, nv_id, now_iso),
        )
        cx.execute(
            """
            INSERT OR IGNORE INTO users(username, password_sha, role, nv_id, display_name, store_id, status)
            VALUES ('ai_scheduler', 'bot_internal', 'ai_assistant', 'ai_scheduler', 'Agent Xếp Lịch 📅', ?, 'active')
            """,
            (store_id,),
        )
        cx.execute(
            """
            INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
            VALUES (?,'ai_scheduler','member','active',?)
            """,
            (conv_general_id, now_iso),
        )

        # Lấy tất cả hội thoại mà nv_id đang tham gia và status = 'active'
        c_rows = cx.execute(
            """
            SELECT c.id, c.store_id, c.type, c.display_name, c.avatar_url, c.is_locked,
                   c.created_at, c.updated_at, p.muted, p.last_read_at
            FROM chat_conversations c
            JOIN chat_participants p ON c.id = p.conversation_id AND p.nv_id = ?
            WHERE c.store_id = ? AND p.status = 'active'
            ORDER BY c.updated_at DESC
            """,
            (nv_id, store_id),
        ).fetchall()

        result = []
        for r in c_rows:
            conv_id = str(r[0])
            conv: dict[str, Any] = {
                "id": conv_id,
                "store_id": str(r[1]),
                "type": str(r[2]),
                "display_name": str(r[3]),
                "avatar_url": str(r[4] or ""),
                "is_locked": bool(r[5]),
                "created_at": str(r[6]),
                "updated_at": str(r[7]),
                "muted": bool(r[8]),
                "last_read_at": str(r[9] or ""),
            }

            # Thành viên
            p_rows = cx.execute(
                """
                SELECT p.nv_id, p.role, p.status, p.muted,
                       COALESCE(u.display_name, p.nv_id) as display_name,
                       COALESCE(u.role, 'nhan_vien') as user_role,
                       COALESCE(u.status, 'active') as user_status
                FROM chat_participants p
                LEFT JOIN users u ON p.nv_id = u.nv_id
                WHERE p.conversation_id = ? AND p.status = 'active'
                """,
                (conv_id,),
            ).fetchall()
            conv["participants"] = [
                {
                    "nv_id": str(pr[0]),
                    "role": str(pr[1]),
                    "status": str(pr[2]),
                    "muted": bool(pr[3]),
                    "display_name": str(pr[4]),
                    "user_role": str(pr[5]),
                    "user_status": str(pr[6]),
                }
                for pr in p_rows
            ]

            if conv["type"] == "direct":
                other = next((p for p in conv["participants"] if p["nv_id"] != nv_id), None)
                if other:
                    conv["display_name"] = other["display_name"]
                    conv["other_user"] = other

            # Đếm số tin chưa đọc dựa trên chat_read_receipts
            receipt = cx.execute(
                "SELECT last_read_message_id, read_at FROM chat_read_receipts WHERE conversation_id = ? AND nv_id = ?",
                (conv_id, nv_id),
            ).fetchone()
            if receipt and receipt[1]:
                read_at = str(receipt[1])
                unread_n = cx.execute(
                    """
                    SELECT COUNT(*) FROM chat_messages
                    WHERE conversation_id = ? AND sender_id != ? AND created_at > ? AND is_unsent = 0
                    """,
                    (conv_id, nv_id, read_at),
                ).fetchone()[0]
            else:
                unread_n = cx.execute(
                    """
                    SELECT COUNT(*) FROM chat_messages
                    WHERE conversation_id = ? AND sender_id != ? AND is_unsent = 0
                    """,
                    (conv_id, nv_id),
                ).fetchone()[0]
            conv["unread_count"] = int(unread_n)

            # Tin nhắn cuối
            last_msg_row = cx.execute(
                """
                SELECT m.id, m.sender_id, m.type, m.content, m.created_at, m.is_unsent,
                       COALESCE(u.display_name, m.sender_id) as sender_name
                FROM chat_messages m
                LEFT JOIN users u ON m.sender_id = u.nv_id
                WHERE m.conversation_id = ?
                ORDER BY m.created_at DESC LIMIT 1
                """,
                (conv_id,),
            ).fetchone()
            if last_msg_row:
                conv["last_message"] = {
                    "id": str(last_msg_row[0]),
                    "sender_id": str(last_msg_row[1]),
                    "type": str(last_msg_row[2]),
                    "content": str(last_msg_row[3]),
                    "created_at": str(last_msg_row[4]),
                    "is_unsent": bool(last_msg_row[5]),
                    "sender_name": str(last_msg_row[6]),
                }
            else:
                conv["last_message"] = None

            result.append(conv)
        return result


def chat_conversation_mute(conv_id: str, nv_id: str, muted: bool = True) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "UPDATE chat_participants SET muted = ? WHERE conversation_id = ? AND nv_id = ?",
            (1 if muted else 0, conv_id, nv_id),
        )


def chat_participants_list(conv_id: str) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            """
            SELECT p.nv_id, p.role, p.status, p.muted, p.last_read_at, p.joined_at, p.archived_at,
                   COALESCE(u.display_name, p.nv_id) as display_name,
                   COALESCE(u.role, 'nhan_vien') as user_role,
                   COALESCE(u.status, 'active') as user_status
            FROM chat_participants p
            LEFT JOIN users u ON p.nv_id = u.nv_id
            WHERE p.conversation_id = ?
            """,
            (conv_id,),
        ).fetchall()
        return [
            {
                "nv_id": str(r[0]),
                "role": str(r[1]),
                "status": str(r[2]),
                "muted": bool(r[3]),
                "last_read_at": str(r[4] or ""),
                "joined_at": str(r[5]),
                "archived_at": str(r[6] or ""),
                "display_name": str(r[7]),
                "user_role": str(r[8]),
                "user_status": str(r[9]),
            }
            for r in rows
        ]


def chat_participant_add(conv_id: str, nv_id: str, role: str = "member") -> None:
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(conversation_id, nv_id) DO UPDATE SET status = 'active'
            """,
            (conv_id, nv_id, role, "active", now),
        )


def chat_participant_remove(conv_id: str, nv_id: str) -> bool:
    """Xóa thành viên khỏi nhóm tự do. Nhóm bị khóa (is_locked=1) không được xóa."""
    init_db()
    with _conn() as cx:
        locked = cx.execute("SELECT is_locked FROM chat_conversations WHERE id=?", (conv_id,)).fetchone()
        if locked and bool(locked[0]):
            return False
        cx.execute(
            "DELETE FROM chat_participants WHERE conversation_id = ? AND nv_id = ?",
            (conv_id, nv_id),
        )
        return True


def chat_message_create(
    conv_id: str,
    sender_id: str,
    content: str = "",
    msg_type: str = "text",
    metadata: dict[str, Any] | None = None,
    reply_to_id: str | None = None,
) -> dict[str, Any]:
    init_db()
    # Kiểm tra quyền: nếu không phải system/copilot/ai_scheduler thì tài khoản phải active và participant status phải active
    if sender_id not in ("system", "copilot", "ai_scheduler"):
        if not user_is_active(sender_id):
            raise ValueError("tai_khoan_da_vo_hieu_hoa")

    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)

    with _conn() as cx:
        # Kiểm tra người gửi có trong phòng và status = 'active' không
        if sender_id not in ("system", "copilot", "ai_scheduler"):
            part = cx.execute(
                "SELECT status FROM chat_participants WHERE conversation_id = ? AND nv_id = ?",
                (conv_id, sender_id),
            ).fetchone()
            if not part or str(part[0]) != "active":
                raise ValueError("khong_phai_thanh_vien_active")

        cx.execute(
            """
            INSERT INTO chat_messages(id, conversation_id, sender_id, type, content, reply_to_id, is_unsent, metadata, created_at)
            VALUES (?,?,?,?,?,?,0,?,?)
            """,
            (msg_id, conv_id, sender_id, msg_type, content, reply_to_id, meta_json, now),
        )
        cx.execute(
            "UPDATE chat_conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id),
        )
        # Đánh dấu đã đọc cho người gửi
        if sender_id != "system":
            cx.execute(
                """
                INSERT INTO chat_read_receipts(conversation_id, nv_id, last_read_message_id, read_at)
                VALUES (?,?,?,?)
                ON CONFLICT(conversation_id, nv_id) DO UPDATE SET last_read_message_id = excluded.last_read_message_id, read_at = excluded.read_at
                """,
                (conv_id, sender_id, msg_id, now),
            )
            cx.execute(
                "UPDATE chat_participants SET last_read_at = ? WHERE conversation_id = ? AND nv_id = ?",
                (now, conv_id, sender_id),
            )
    return chat_message_get(msg_id) or {"id": msg_id, "conversation_id": conv_id, "content": content}


def chat_message_get(message_id: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT m.id, m.conversation_id, m.sender_id, m.type, m.content,
                   m.reply_to_id, m.is_unsent, m.edited_at, m.metadata, m.created_at,
                   COALESCE(u.display_name, CASE WHEN m.sender_id = 'copilot' THEN 'AG-Copilot 🤖' WHEN m.sender_id = 'ai_scheduler' THEN 'Agent Xếp Lịch 📅' ELSE m.sender_id END) as sender_name,
                   COALESCE(u.role, CASE WHEN m.sender_id IN ('copilot', 'ai_scheduler') THEN 'ai_assistant' ELSE 'nhan_vien' END) as sender_role
            FROM chat_messages m
            LEFT JOIN users u ON m.sender_id = u.nv_id
            WHERE m.id = ?
            """,
            (message_id,),
        ).fetchone()
        if not row:
            return None

        # Reactions
        react_rows = cx.execute(
            """
            SELECT r.emoji, r.nv_id, COALESCE(u.display_name, r.nv_id) as display_name
            FROM chat_reactions r
            LEFT JOIN users u ON r.nv_id = u.nv_id
            WHERE r.message_id = ?
            """,
            (message_id,),
        ).fetchall()
        reactions: dict[str, list[dict[str, str]]] = {}
        for r_emoji, r_nv, r_name in react_rows:
            reactions.setdefault(str(r_emoji), []).append({"nv_id": str(r_nv), "name": str(r_name)})

        # Reply snippet
        reply_snippet = None
        reply_id = row[5]
        if reply_id:
            r_msg = cx.execute(
                """
                SELECT m.id, m.sender_id, m.content, m.type,
                       COALESCE(u.display_name, m.sender_id) as sender_name
                FROM chat_messages m
                LEFT JOIN users u ON m.sender_id = u.nv_id
                WHERE m.id = ?
                """,
                (str(reply_id),),
            ).fetchone()
            if r_msg:
                reply_snippet = {
                    "id": str(r_msg[0]),
                    "sender_id": str(r_msg[1]),
                    "content": str(r_msg[2]),
                    "type": str(r_msg[3]),
                    "sender_name": str(r_msg[4]),
                }

        meta: dict[str, Any] = {}
        try:
            meta = json.loads(row[8]) if row[8] else {}
        except Exception:
            pass

        return {
            "id": str(row[0]),
            "conversation_id": str(row[1]),
            "sender_id": str(row[2]),
            "type": str(row[3]),
            "content": str(row[4]),
            "reply_to_id": str(row[5]) if row[5] else None,
            "reply_snippet": reply_snippet,
            "is_unsent": bool(row[6]),
            "edited_at": str(row[7]) if row[7] else None,
            "metadata": meta,
            "created_at": str(row[9]),
            "sender_name": str(row[10]),
            "sender_role": str(row[11]),
            "reactions": reactions,
        }


def chat_message_edit(message_id: str, sender_id: str, new_content: str) -> dict[str, Any] | None:
    """Sửa tin nhắn (trong vòng 15 phút, chỉ tác giả mới được sửa)."""
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        msg = cx.execute(
            "SELECT sender_id, created_at, is_unsent FROM chat_messages WHERE id = ?",
            (message_id,),
        ).fetchone()
        if not msg:
            return None
        if str(msg[0]) != sender_id or bool(msg[2]):
            return None
        # Kiểm tra thời hạn 15 phút (900s)
        try:
            created_dt = datetime.fromisoformat(str(msg[1]).replace("Z", "+00:00"))
            if (datetime.now(UTC) - created_dt).total_seconds() > 900:
                return None
        except Exception:
            pass

        cx.execute(
            "UPDATE chat_messages SET content = ?, edited_at = ? WHERE id = ?",
            (new_content.strip(), now, message_id),
        )
    return chat_message_get(message_id)


def chat_message_delete(message_id: str, sender_id: str) -> dict[str, Any] | None:
    """Thu hồi tin nhắn (is_unsent = 1)."""
    init_db()
    with _conn() as cx:
        msg = cx.execute(
            "SELECT sender_id, conversation_id FROM chat_messages WHERE id = ?",
            (message_id,),
        ).fetchone()
        if not msg:
            return None
        s_id = str(msg[0])
        user_role = cx.execute("SELECT role FROM users WHERE nv_id = ?", (sender_id,)).fetchone()
        role_str = str(user_role[0]) if user_role else "nhan_vien"
        if s_id != sender_id and role_str not in ("quan_ly", "chu_quan"):
            return None

        cx.execute(
            """
            UPDATE chat_messages
            SET is_unsent = 1, content = 'Tin nhắn đã được thu hồi'
            WHERE id = ?
            """,
            (message_id,),
        )
    return chat_message_get(message_id)


def chat_message_react(message_id: str, nv_id: str, emoji: str) -> dict[str, Any]:
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        existing = cx.execute(
            "SELECT emoji FROM chat_reactions WHERE message_id = ? AND nv_id = ?",
            (message_id, nv_id),
        ).fetchone()
        if existing and str(existing[0]) == emoji:
            cx.execute(
                "DELETE FROM chat_reactions WHERE message_id = ? AND nv_id = ?",
                (message_id, nv_id),
            )
        else:
            cx.execute(
                """
                INSERT INTO chat_reactions(message_id, nv_id, emoji, created_at)
                VALUES (?,?,?,?)
                ON CONFLICT(message_id, nv_id) DO UPDATE SET emoji = excluded.emoji, created_at = excluded.created_at
                """,
                (message_id, nv_id, emoji, now),
            )
    return chat_message_get(message_id) or {"id": message_id}


def chat_messages_list(conv_id: str, limit: int = 50, before_id: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        if before_id:
            b_row = cx.execute("SELECT created_at FROM chat_messages WHERE id = ?", (before_id,)).fetchone()
            if b_row:
                before_time = str(b_row[0])
                rows = cx.execute(
                    """
                    SELECT id FROM chat_messages
                    WHERE conversation_id = ? AND created_at < ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (conv_id, before_time, limit),
                ).fetchall()
            else:
                rows = []
        else:
            rows = cx.execute(
                """
                SELECT id FROM chat_messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (conv_id, limit),
            ).fetchall()

    msg_ids = [str(r[0]) for r in reversed(rows)]
    return [m for mid in msg_ids if (m := chat_message_get(mid)) is not None]


def chat_messages_search(
    query: str, nv_id: str, conv_id: str | None = None, store_id: str = "quan_01"
) -> list[dict[str, Any]]:
    """Tìm kiếm nội dung tin nhắn trong các hội thoại mà người dùng có quyền xem."""
    init_db()
    q = f"%{query.strip()}%"
    with _conn() as cx:
        if conv_id:
            rows = cx.execute(
                """
                SELECT m.id FROM chat_messages m
                JOIN chat_participants p ON m.conversation_id = p.conversation_id AND p.nv_id = ?
                WHERE m.conversation_id = ? AND m.content LIKE ? AND m.is_unsent = 0 AND p.status = 'active'
                ORDER BY m.created_at DESC LIMIT 50
                """,
                (nv_id, conv_id, q),
            ).fetchall()
        else:
            rows = cx.execute(
                """
                SELECT m.id FROM chat_messages m
                JOIN chat_conversations c ON m.conversation_id = c.id
                JOIN chat_participants p ON m.conversation_id = p.conversation_id AND p.nv_id = ?
                WHERE c.store_id = ? AND m.content LIKE ? AND m.is_unsent = 0 AND p.status = 'active'
                ORDER BY m.created_at DESC LIMIT 50
                """,
                (nv_id, store_id, q),
            ).fetchall()
    return [m for r in rows if (m := chat_message_get(str(r[0]))) is not None]


def chat_read_receipts_update(conv_id: str, nv_id: str, message_id: str) -> list[dict[str, Any]]:
    """Cập nhật trạng thái đã xem (Seen receipt)."""
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO chat_read_receipts(conversation_id, nv_id, last_read_message_id, read_at)
            VALUES (?,?,?,?)
            ON CONFLICT(conversation_id, nv_id) DO UPDATE SET last_read_message_id = excluded.last_read_message_id, read_at = excluded.read_at
            """,
            (conv_id, nv_id, message_id, now),
        )
        cx.execute(
            "UPDATE chat_participants SET last_read_at = ? WHERE conversation_id = ? AND nv_id = ?",
            (now, conv_id, nv_id),
        )
    return chat_read_receipts(conv_id)


def chat_message_read(conv_id: str, nv_id: str, message_id: str) -> list[dict[str, Any]]:
    """Compatibility name used by the WebSocket chat service."""
    return chat_read_receipts_update(conv_id, nv_id, message_id)


def chat_message_pin(message_id: str, sender_id: str, pinned: bool = True) -> dict[str, Any] | None:
    """Pin state is stored in message metadata for the current chat schema."""
    message = chat_message_get(message_id)
    if not message:
        return None
    init_db()
    with _conn() as cx:
        user_role = cx.execute("SELECT role FROM users WHERE nv_id = ?", (sender_id,)).fetchone()
        role_str = str(user_role[0]) if user_role else "nhan_vien"
        if message.get("sender_id") != sender_id and role_str not in ("quan_ly", "chu_quan"):
            return None
        metadata = dict(message.get("metadata") or {})
        metadata["pinned"] = pinned
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        cx.execute(
            "UPDATE chat_messages SET metadata=?, edited_at=? WHERE id=?",
            (json.dumps(metadata, ensure_ascii=False), now, message_id),
        )
    return chat_message_get(message_id)


def chat_read_receipts(conv_id: str) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            """
            SELECT r.nv_id, COALESCE(u.display_name, r.nv_id) as display_name,
                   r.last_read_message_id, r.read_at, COALESCE(u.role, 'nhan_vien') as role
            FROM chat_read_receipts r
            LEFT JOIN users u ON r.nv_id = u.nv_id
            WHERE r.conversation_id = ?
            """,
            (conv_id,),
        ).fetchall()
        return [
            {
                "nv_id": str(r[0]),
                "display_name": str(r[1]),
                "last_read_message_id": str(r[2]),
                "read_at": str(r[3]),
                "role": str(r[4]),
            }
            for r in rows
        ]


def chat_unread_count_total(nv_id: str, store_id: str = "quan_01") -> int:
    init_db()
    convs = chat_conversation_list_for_user(nv_id, store_id)
    return sum(c.get("unread_count", 0) for c in convs)


# ── Sơ đồ Bàn & Đặt Bàn Tự Động (Auto Reservation) ──────────────────────────


def _seed_tables_neu_trong(cx: sqlite3.Connection) -> None:
    count = cx.execute("SELECT COUNT(*) FROM ban_an").fetchone()[0]
    if count == 0:
        default_tables = [
            ("B101", "quan_01", "Bàn 101", 2, "Tầng 1 - Cửa sổ", json.dumps(["B102"])),
            ("B102", "quan_01", "Bàn 102", 2, "Tầng 1 - Cửa sổ", json.dumps(["B101"])),
            ("B103", "quan_01", "Bàn 103", 2, "Tầng 1 - Trong nhà", json.dumps([])),
            ("B104", "quan_01", "Bàn 104", 2, "Tầng 1 - Trong nhà", json.dumps([])),
            ("B105", "quan_01", "Bàn 105", 4, "Tầng 1 - Sân vườn", json.dumps([])),
            ("B106", "quan_01", "Bàn 106", 4, "Tầng 1 - Sân vườn", json.dumps([])),
            ("B201", "quan_01", "Bàn 201", 4, "Tầng 2 - Yên tĩnh", json.dumps([])),
            ("B202", "quan_01", "Bàn 202", 4, "Tầng 2 - Yên tĩnh", json.dumps([])),
            ("B203", "quan_01", "Bàn 203", 4, "Tầng 2 - Nhóm lớn", json.dumps(["B204"])),
            ("B204", "quan_01", "Bàn 204", 4, "Tầng 2 - Nhóm lớn", json.dumps(["B203"])),
        ]
        cx.executemany(
            """
            INSERT INTO ban_an(id, store_id, ten_ban, suc_chua, vi_tri, can_combine_with)
            VALUES (?,?,?,?,?,?)
            """,
            default_tables,
        )


def table_list(store_id: str = "quan_01") -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT * FROM ban_an WHERE store_id=? AND trang_thai_hoat_dong=1 ORDER BY id ASC",
            (store_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["can_combine_with"] = json.loads(d.get("can_combine_with") or "[]")
            except Exception:
                d["can_combine_with"] = []
            result.append(d)
        return result


def table_get(table_id: str, store_id: str = "quan_01") -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        r = cx.execute(
            "SELECT * FROM ban_an WHERE id=? AND store_id=?", (table_id, store_id)
        ).fetchone()
        if not r:
            return None
        d = dict(r)
        try:
            d["can_combine_with"] = json.loads(d.get("can_combine_with") or "[]")
        except Exception:
            d["can_combine_with"] = []
        return d


def reservation_create(record: dict[str, Any]) -> str:
    init_db()
    res_id = record.get("id") or f"res_{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    table_ids = record.get("table_ids") or []
    if isinstance(table_ids, list):
        table_ids_str = json.dumps(table_ids)
    else:
        table_ids_str = str(table_ids)

    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO dat_ban(
                id, store_id, psid, customer_name, phone, booking_time, duration_minutes,
                party_size, table_ids, status, source, notes, idempotency_key, notified_nv_id,
                notification_acked_at, cancelled_by, cancelled_reason, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                res_id,
                record.get("store_id", "quan_01"),
                record.get("psid", ""),
                record.get("customer_name", ""),
                record.get("phone", ""),
                record.get("booking_time", ""),
                int(record.get("duration_minutes", 120)),
                int(record.get("party_size", 2)),
                table_ids_str,
                record.get("status", "confirmed"),
                record.get("source", "ai_auto"),
                record.get("notes", ""),
                record.get("idempotency_key", ""),
                record.get("notified_nv_id"),
                record.get("notification_acked_at"),
                record.get("cancelled_by"),
                record.get("cancelled_reason"),
                record.get("created_at") or now,
                record.get("updated_at") or now,
            ),
        )
        cx.execute(
            """
            INSERT INTO dat_ban_lich_su(dat_ban_id, hanh_dong, trang_thai_cu, trang_thai_moi, thuc_hien_boi, ly_do, thoi_gian)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                res_id,
                "tao_moi",
                None,
                record.get("status", "confirmed"),
                record.get("source", "ai_auto"),
                "Khách đặt bàn",
                now,
            ),
        )
    return res_id


def reservation_get(res_id: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        r = cx.execute("SELECT * FROM dat_ban WHERE id=?", (res_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        try:
            d["table_ids"] = json.loads(d.get("table_ids") or "[]")
        except Exception:
            d["table_ids"] = []
        return d


def reservation_get_by_idempotency(idem_key: str, store_id: str = "quan_01") -> dict[str, Any] | None:
    if not idem_key:
        return None
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        r = cx.execute(
            "SELECT * FROM dat_ban WHERE store_id=? AND idempotency_key=? AND status NOT IN ('cancelled', 'no_show')",
            (store_id, idem_key),
        ).fetchone()
        if not r:
            return None
        d = dict(r)
        try:
            d["table_ids"] = json.loads(d.get("table_ids") or "[]")
        except Exception:
            d["table_ids"] = []
        return d


def reservation_list(
    store_id: str = "quan_01",
    date: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        query = "SELECT * FROM dat_ban WHERE store_id=?"
        params: list[Any] = [store_id]
        if date:
            query += " AND booking_time LIKE ?"
            params.append(f"{date}%")
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY booking_time ASC LIMIT ?"
        params.append(limit)

        rows = cx.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["table_ids"] = json.loads(d.get("table_ids") or "[]")
            except Exception:
                d["table_ids"] = []
            result.append(d)
        return result


def reservation_update_status(
    res_id: str,
    new_status: str,
    actor: str = "system",
    reason: str = "",
    cancelled_by: str | None = None,
) -> bool:
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        cur = cx.execute("SELECT status FROM dat_ban WHERE id=?", (res_id,)).fetchone()
        if not cur:
            return False
        old_status = cur["status"]
        if old_status == new_status:
            return True

        if cancelled_by:
            cx.execute(
                """
                UPDATE dat_ban
                SET status=?, updated_at=?, cancelled_by=?, cancelled_reason=?
                WHERE id=?
                """,
                (new_status, now, cancelled_by, reason, res_id),
            )
        else:
            cx.execute(
                "UPDATE dat_ban SET status=?, updated_at=? WHERE id=?",
                (new_status, now, res_id),
            )

        cx.execute(
            """
            INSERT INTO dat_ban_lich_su(dat_ban_id, hanh_dong, trang_thai_cu, trang_thai_moi, thuc_hien_boi, ly_do, thoi_gian)
            VALUES (?,?,?,?,?,?,?)
            """,
            (res_id, f"chuyen_{new_status}", old_status, new_status, actor, reason, now),
        )
        return True


def reservation_find_active_by_psid(psid: str, store_id: str = "quan_01") -> list[dict[str, Any]]:
    if not psid:
        return []
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT * FROM dat_ban
            WHERE store_id=? AND psid=? AND status IN ('held', 'confirmed')
            ORDER BY booking_time ASC
            """,
            (store_id, psid),
        ).fetchall()
        res = []
        for r in rows:
            d = dict(r)
            try:
                d["table_ids"] = json.loads(d.get("table_ids") or "[]")
            except Exception:
                d["table_ids"] = []
            res.append(d)
        return res


def reservation_find_active_by_phone(phone: str, store_id: str = "quan_01") -> list[dict[str, Any]]:
    if not phone:
        return []
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT * FROM dat_ban
            WHERE store_id=? AND phone=? AND status IN ('held', 'confirmed')
            ORDER BY booking_time ASC
            """,
            (store_id, phone),
        ).fetchall()
        res = []
        for r in rows:
            d = dict(r)
            try:
                d["table_ids"] = json.loads(d.get("table_ids") or "[]")
            except Exception:
                d["table_ids"] = []
            res.append(d)
        return res


def reservation_count_no_shows(phone: str = "", psid: str = "", store_id: str = "quan_01") -> int:
    init_db()
    with _conn() as cx:
        conds = []
        params: list[Any] = [store_id]
        if phone:
            conds.append("phone=?")
            params.append(phone)
        if psid:
            conds.append("psid=?")
            params.append(psid)
        if not conds:
            return 0
        sql = f"SELECT COUNT(*) FROM dat_ban WHERE store_id=? AND status='no_show' AND ({' OR '.join(conds)})"
        row = cx.execute(sql, params).fetchone()
        return int(row[0]) if row else 0


def thong_bao_ca_create(row: dict[str, Any]) -> str:
    init_db()
    tb_id = row.get("id") or f"tb_{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO thong_bao_ca(id, store_id, dat_ban_id, ca_id, nv_id, tieu_de, noi_dung, da_xem, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                tb_id,
                row.get("store_id", "quan_01"),
                row.get("dat_ban_id", ""),
                row.get("ca_id", ""),
                row.get("nv_id", ""),
                row.get("tieu_de", "Thông báo đặt bàn"),
                row.get("noi_dung", ""),
                int(row.get("da_xem", 0)),
                row.get("created_at") or now,
            ),
        )
    return tb_id


def thong_bao_ca_list(nv_id: str, unread_only: bool = False, store_id: str = "quan_01") -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        cx.row_factory = sqlite3.Row
        sql = "SELECT * FROM thong_bao_ca WHERE store_id=? AND nv_id=?"
        params: list[Any] = [store_id, nv_id]
        if unread_only:
            sql += " AND da_xem=0"
        sql += " ORDER BY created_at DESC LIMIT 50"
        rows = cx.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def thong_bao_ca_ack(thong_bao_id: str, nv_id: str) -> bool:
    init_db()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _conn() as cx:
        res = cx.execute(
            "UPDATE thong_bao_ca SET da_xem=1 WHERE id=? AND nv_id=?",
            (thong_bao_id, nv_id),
        )
        if res.rowcount > 0:
            # Also update dat_ban notification_acked_at
            tb = cx.execute("SELECT dat_ban_id FROM thong_bao_ca WHERE id=?", (thong_bao_id,)).fetchone()
            if tb and tb[0]:
                cx.execute(
                    "UPDATE dat_ban SET notification_acked_at=? WHERE id=? AND notification_acked_at IS NULL",
                    (now, tb[0]),
                )
            return True
        return False

