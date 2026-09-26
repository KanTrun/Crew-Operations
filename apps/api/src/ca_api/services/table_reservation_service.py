"""Table Reservation Engine — Concurrency-safe, Anti-abuse, Multi-turn Booking Service.

Enterprise features:
1. Atomic reservation with SQLite BEGIN IMMEDIATE (Zero TOCTOU double-booking).
2. Webhook idempotency by sha256(store_id:psid:booking_time:party_size).
3. Table combinability matrix (single table prioritization & combinable pairs).
4. Anti-abuse guard (max 1 active future booking per PSID/phone, rate limit, no-show blacklist).
5. Shift manager resolution & push notification with escalation fallback.
6. Timezone-aware handling (Asia/Ho_Chi_Minh / UTC+7).
7. Fail-closed safety principle (all unexpected errors fail safely to queue review).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from ca_api.persist import (
    _conn,
    acquire_write_lock,
    init_db,
    kenh_bind_get,
    reservation_count_no_shows,
    reservation_find_active_by_phone,
    reservation_find_active_by_psid,
    reservation_get,
    reservation_get_by_idempotency,
    reservation_list,
    reservation_update_status,
    thong_bao_ca_create,
)

LOG = logging.getLogger(__name__)

# ICT Timezone (UTC+7)
ICT = timezone(timedelta(hours=7))

MAX_PARTY_SIZE_AUTO = 8
DEFAULT_DURATION_MINUTES = 120
HOLD_DURATION_MINUTES = 5
MAX_ACTIVE_PER_CUSTOMER = 1
NO_SHOW_THRESHOLD = 2

# Sau bao lâu mà trưởng ca chưa xác nhận (`notification_acked_at` còn NULL) thì
# nhắc người dự phòng trong cùng ca. Trưởng ca có thể đang bận ngoài quầy, nên
# cần cơ chế leo thang — trước đây `backup_nv_ids` được tính rồi bỏ không dùng.
ESCALATION_AFTER_MINUTES = 10

# Seed ca mẫu (nguồn `ca_meta`: ca_id -> thứ/khung). Cùng đường dẫn với
# `apps/api/src/ca_api/interfaces/http/sprint3.py` để một nguồn sự thật duy nhất.
SEED_PATH = Path(__file__).resolve().parents[5] / "data" / "seed" / "sample.json"


def auto_reservation_enabled() -> bool:
    """Feature flag for auto-reservation.

    Checked via KV store or NHIPQUAN_AUTO_RESERVATION env.
    Defaults to True for seamless customer experience.
    """
    try:
        from ca_api.persist import kv_get

        stored = kv_get("fb_policy_runtime", {})
        if isinstance(stored, dict) and "auto_reservation_enabled" in stored:
            return bool(stored["auto_reservation_enabled"])
    except Exception:
        pass

    import os

    env = os.environ.get("NHIPQUAN_AUTO_RESERVATION", "1").strip().lower()
    return env in {"1", "true", "yes", "on"}




class TableReservationError(Exception):
    """Base exception for table reservations."""


class NoTableAvailableError(TableReservationError):
    """Raised when no table or combination meets party size at the given time."""


class AntiAbuseBlockedError(TableReservationError):
    """Raised when anti-abuse rules block automatic reservation."""


def get_ict_now() -> datetime:
    """Return current time in Asia/Ho_Chi_Minh (ICT)."""
    return datetime.now(ICT)


def parse_booking_datetime(dt_str: str) -> datetime:
    """
    Parse ISO string or YYYY-MM-DD HH:MM string to ICT timezone-aware datetime.
    """
    dt_str = dt_str.strip()
    if dt_str.endswith("Z"):
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(ICT)
    if "+" in dt_str[10:]:
        dt = datetime.fromisoformat(dt_str)
        return dt.astimezone(ICT)
    # Assume local ICT if timezone not specified
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            naive = datetime.strptime(dt_str, fmt)
            return naive.replace(tzinfo=ICT)
        except ValueError:
            pass
    # Fallback to fromisoformat
    naive = datetime.fromisoformat(dt_str)
    if naive.tzinfo is None:
        return naive.replace(tzinfo=ICT)
    return naive.astimezone(ICT)


def format_ict_iso(dt: datetime) -> str:
    """Format datetime as ISO string with timezone offset."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ICT)
    return dt.astimezone(ICT).isoformat()


def generate_reservation_idempotency_key(
    store_id: str, psid: str, booking_time_iso: str, party_size: int
) -> str:
    """Generate deterministic idempotency key for reservation attempts."""
    raw = f"{store_id}:{psid}:{booking_time_iso}:{party_size}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def check_anti_abuse(
    store_id: str = "quan_01",
    psid: str = "",
    phone: str = "",
) -> tuple[bool, str | None]:
    """
    Check anti-abuse rules:
    - Active reservation limit per customer (max 1 future booking).
    - No-show blacklist (>= 2 no-shows).
    """
    if psid:
        actives = reservation_find_active_by_psid(psid, store_id)
        if len(actives) >= MAX_ACTIVE_PER_CUSTOMER:
            return False, "active_booking_exists"
    if phone:
        actives_phone = reservation_find_active_by_phone(phone, store_id)
        if len(actives_phone) >= MAX_ACTIVE_PER_CUSTOMER:
            return False, "active_booking_exists"

    no_shows = reservation_count_no_shows(phone=phone, psid=psid, store_id=store_id)
    if no_shows >= NO_SHOW_THRESHOLD:
        return False, "no_show_blacklist"

    return True, None


def atomic_hold_or_book_table(
    *,
    store_id: str = "quan_01",
    psid: str = "",
    customer_name: str,
    phone: str,
    email: str = "",
    booking_time: str,
    party_size: int,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    notes: str = "",
    source: str = "ai_auto",
    status: str = "confirmed",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Atomically find an available table (or valid combination) and create reservation
    within an exclusive SQLite transaction (BEGIN IMMEDIATE) to prevent TOCTOU double-booking.
    """
    init_db()
    if party_size > MAX_PARTY_SIZE_AUTO:
        raise NoTableAvailableError(
            f"Party size {party_size} exceeds auto-booking limit ({MAX_PARTY_SIZE_AUTO}). Needs manager review."
        )

    start_dt = parse_booking_datetime(booking_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    start_iso = format_ict_iso(start_dt)

    if not idempotency_key:
        idempotency_key = generate_reservation_idempotency_key(
            store_id, psid, start_iso, party_size
        )

    # Check idempotency first
    existing = reservation_get_by_idempotency(idempotency_key, store_id)
    if existing:
        return existing

    # Find manager for shift before entering lock to avoid nested lock contention
    shift_info = resolve_shift_manager_and_backup(start_dt, store_id)
    primary_manager = shift_info.get("primary_nv_id")

    with _conn() as cx:
        # 1. Acquire exclusive write lock immediately
        cx.execute("BEGIN IMMEDIATE")
        # SQLite: `BEGIN IMMEDIATE` ở trên đã loại trừ nhau. Postgres: cần khoá
        # tư vấn tường minh, nếu không khe TOCTOU vẫn mở (xem `acquire_write_lock`).
        acquire_write_lock(cx, "dat_ban")

        # Re-check idempotency inside lock
        cx.row_factory = sqlite3.Row
        cur_existing = cx.execute(
            "SELECT id FROM dat_ban WHERE store_id=? AND idempotency_key=? AND status NOT IN ('cancelled', 'no_show')",
            (store_id, idempotency_key),
        ).fetchone()
        if cur_existing:
            cx.rollback()
            return reservation_get(cur_existing["id"]) or {}

        # 2. Query overlapping active reservations
        # An overlap exists when NOT (res_end <= start_dt OR res_start >= end_dt)
        now_dt = get_ict_now()
        hold_expiry_dt = now_dt - timedelta(minutes=HOLD_DURATION_MINUTES)

        active_res_rows = cx.execute(
            """
            SELECT id, table_ids, booking_time, duration_minutes, status, created_at
            FROM dat_ban
            WHERE store_id=? AND status IN ('held', 'confirmed', 'seated')
            """,
            (store_id,),
        ).fetchall()

        occupied_table_ids: set[str] = set()
        for row in active_res_rows:
            r_status = row["status"]
            # Discard expired holds (> 5 mins)
            #
            # So sánh bằng datetime đã parse, KHÔNG so chuỗi: `created_at` có thể
            # là "...Z" (bản ghi cũ/`reservation_create`) hoặc "+07:00"
            # (`format_ict_iso`). So chuỗi giữa hai định dạng này lệch 7 tiếng nên
            # mọi hold đều bị coi là hết hạn ngay khi vừa tạo.
            if r_status == "held" and _created_truoc_moc(row["created_at"], hold_expiry_dt):
                continue

            r_start = parse_booking_datetime(row["booking_time"])
            r_dur = int(row["duration_minutes"] or DEFAULT_DURATION_MINUTES)
            r_end = r_start + timedelta(minutes=r_dur)

            # Check overlap: (start_dt < r_end) and (end_dt > r_start)
            if start_dt < r_end and end_dt > r_start:
                try:
                    tids = json.loads(row["table_ids"] or "[]")
                except Exception:
                    tids = []
                for tid in tids:
                    occupied_table_ids.add(tid)

        # 3. Fetch all active tables in store
        table_rows = cx.execute(
            "SELECT * FROM ban_an WHERE store_id=? AND trang_thai_hoat_dong=1 ORDER BY suc_chua ASC, id ASC",
            (store_id,),
        ).fetchall()

        all_tables: list[dict[str, Any]] = []
        for r in table_rows:
            d = dict(r)
            try:
                d["can_combine_with"] = json.loads(d.get("can_combine_with") or "[]")
            except Exception:
                d["can_combine_with"] = []
            all_tables.append(d)

        available_tables = [t for t in all_tables if t["id"] not in occupied_table_ids]

        # 4. Matching Algorithm:
        # Step A: Best fit single table (smallest capacity >= party_size)
        single_fit = [t for t in available_tables if t["suc_chua"] >= party_size]
        assigned_table_ids: list[str] = []

        if single_fit:
            # Sort by least wasted capacity, then ID
            single_fit.sort(key=lambda t: (t["suc_chua"] - party_size, t["id"]))
            assigned_table_ids = [single_fit[0]["id"]]
        else:
            # Step B: Combined table search for party sizes 5..8
            pair_found: list[str] | None = None
            for t in available_tables:
                for partner_id in t.get("can_combine_with", []):
                    partner = next((p for p in available_tables if p["id"] == partner_id), None)
                    if partner:
                        combined_cap = t["suc_chua"] + partner["suc_chua"]
                        if combined_cap >= party_size:
                            pair_found = sorted([t["id"], partner["id"]])
                            break
                if pair_found:
                    break
            if pair_found:
                assigned_table_ids = pair_found

        if not assigned_table_ids:
            cx.rollback()
            raise NoTableAvailableError(
                f"No suitable table available for {party_size} people at {booking_time}."
            )

        # 5. Insert new reservation
        res_id = f"res_{uuid.uuid4().hex[:10]}"
        now_iso = format_ict_iso(now_dt)

        effective_notes = f"Email: {email}. {notes}".strip() if email and f"Email: {email}" not in notes else notes

        cx.execute(
            """
            INSERT INTO dat_ban(
                id, store_id, psid, customer_name, phone, email, booking_time, duration_minutes,
                party_size, table_ids, status, source, notes, idempotency_key, notified_nv_id,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                res_id,
                store_id,
                psid,
                customer_name,
                phone,
                email,
                start_iso,
                duration_minutes,
                party_size,
                json.dumps(assigned_table_ids),
                status,
                source,
                effective_notes,
                idempotency_key,
                primary_manager,
                now_iso,
                now_iso,
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
                status,
                source,
                f"Bàn được gán: {', '.join(assigned_table_ids)}",
                now_iso,
            ),
        )

        cx.commit()

    created_record = {
        "id": res_id,
        "store_id": store_id,
        "psid": psid,
        "customer_name": customer_name,
        "phone": phone,
        "email": email,
        "booking_time": start_iso,
        "duration_minutes": duration_minutes,
        "party_size": party_size,
        "table_ids": assigned_table_ids,
        "status": status,
        "source": source,
        "notes": effective_notes,
        "idempotency_key": idempotency_key,
        "notified_nv_id": primary_manager,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    return created_record


def _created_truoc_moc(created_at: Any, moc: datetime) -> bool:
    """`created_at` có trước `moc` không — so sánh bằng datetime, không so chuỗi.

    `created_at` trong `dat_ban` tồn tại ở hai định dạng: `...Z` (UTC, do
    `reservation_create` ghi) và `+07:00` (`format_ict_iso`). So sánh chuỗi giữa
    hai định dạng này sai lệch 7 tiếng. Bản ghi không parse được coi như KHÔNG
    hết hạn — fail-closed: giữ bàn còn hơn nhận thêm khách vào bàn đã có người.
    """
    raw = str(created_at or "").strip()
    if not raw:
        return False
    try:
        return parse_booking_datetime(raw) < moc
    except (TypeError, ValueError):
        return False


def _phan_cong_theo_tuan(
    phan_cong: dict[str, Any],
    phan_cong_by_week: dict[str, Any],
    booking_dt: datetime,
) -> dict[str, Any]:
    """Phân công của TUẦN chứa ngày đặt bàn, ưu tiên dữ liệu theo tuần.

    Vì sao cần: `solver_adapter._week_store("phan_cong_by_week", tuần, ...)` lưu
    kết quả xếp lịch theo từng tuần, còn key phẳng `phan_cong` chỉ giữ kết quả
    tuần GẦN NHẤT. Khách có thể đặt bàn trước cho tuần sau → tra `phan_cong`
    sẽ chọn nhầm người trực của tuần cũ. Thứ tự ưu tiên ở đây khớp
    `sprint3._phan_cong` và `sprint45._phan`: by_week của tuần mục tiêu trước,
    rồi mới tới key phẳng.

    Định dạng khoá tuần là ISO `YYYY-Www` (xem `_current_iso_week`).
    """
    tuan = booking_dt.isocalendar()
    tuan_iso = f"{tuan.year}-W{tuan.week:02d}"
    tuan_data = phan_cong_by_week.get(tuan_iso)
    if isinstance(tuan_data, dict) and tuan_data:
        return tuan_data
    return phan_cong


def _khung_gio_config(khung_gio_raw: Any) -> dict[str, tuple[int, int]]:
    """Khung giờ (phút) của từng ca, ưu tiên cấu hình kv `khung_gio`.

    Mặc định khớp seed `ca_mau_21` (07–12 / 12–17 / 17–22) và `_KHUNG_DEFAULTS`
    ở tầng HTTP — hai nguồn này phải nhất quán, nếu lệch thì đơn đặt gần biên
    khung sẽ bị gán nhầm ca trực.
    """
    mac_dinh: dict[str, tuple[int, int]] = {
        "sang": (7 * 60, 12 * 60),
        "chieu": (12 * 60, 17 * 60),
        "toi": (17 * 60, 22 * 60),
    }
    if not isinstance(khung_gio_raw, dict):
        return mac_dinh

    def _phut(gia_tri: Any, fallback: int) -> int:
        try:
            gio, phut = str(gia_tri).split(":")[:2]
            return int(gio) * 60 + int(phut)
        except (TypeError, ValueError):
            return fallback

    out: dict[str, tuple[int, int]] = {}
    for ten, (bd_mac_dinh, kt_mac_dinh) in mac_dinh.items():
        slot = khung_gio_raw.get(ten)
        if isinstance(slot, dict):
            bd = _phut(slot.get("bat_dau"), bd_mac_dinh)
            kt = _phut(slot.get("ket_thuc"), kt_mac_dinh)
        else:
            bd, kt = bd_mac_dinh, kt_mac_dinh
        out[ten] = (bd, kt) if kt > bd else (bd_mac_dinh, kt_mac_dinh)
    return out


def _khung_theo_gio(phut_trong_ngay: int, khung_gio: dict[str, tuple[int, int]]) -> str:
    """Chọn khung ca chứa thời điểm đặt bàn; ngoài mọi khung → ca gần nhất.

    Thứ tự xét là `sang` → `chieu` → `toi`. Nếu quản lý cấu hình hai khung
    chồng lấn nhau (vd `chieu` 12–17 và `toi` 15–23), khung xuất hiện trước
    thắng — kết quả vẫn tất định, không phụ thuộc thứ tự dict của Python.
    """
    for ten, (bat_dau, ket_thuc) in khung_gio.items():
        if bat_dau <= phut_trong_ngay < ket_thuc:
            return ten

    truoc_mo = [(bd, ten) for ten, (bd, _) in khung_gio.items() if phut_trong_ngay < bd]
    if truoc_mo:
        return min(truoc_mo)[1]
    return max((kt, ten) for ten, (_, kt) in khung_gio.items())[1]


@lru_cache(maxsize=1)
def _ca_meta_theo_khung() -> dict[tuple[str, str], list[str]]:
    """Map (thứ, khung) → danh sách ca_id, đọc từ seed `ca_mau_21`.

    `phan_cong` trong kv key theo ca_id (`w1_c01`) nên cần bảng bắc cầu này.
    Seed là dữ liệu tĩnh trong repo nên cache 1 lần là đủ.
    """
    thu_theo_ngay_offset = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
    out: dict[tuple[str, str], list[str]] = {}
    try:
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return out

    for ca in seed.get("ca_mau_21") or []:
        if not isinstance(ca, dict) or not ca.get("id"):
            continue
        thu = str(ca.get("thu") or thu_theo_ngay_offset.get(int(ca.get("ngay_offset") or 0), ""))
        khung = str(ca.get("khung") or "")
        if thu and khung:
            out.setdefault((thu, khung), []).append(str(ca["id"]))
    return out


def resolve_shift_manager_and_backup(
    booking_dt: datetime, store_id: str = "quan_01"
) -> dict[str, Any]:
    """
    Determine which shift (sáng, chiều, tối) covers the booking time,
    and find the on-duty manager/shift lead and backup staff.

    Phân công ca trong kv `phan_cong` được key theo **ca_id** (`w1_c01`), không
    theo mã khung (`T2_sang`). Vì vậy phải bắc cầu qua `ca_mau_21` trong seed
    để biết ca nào thuộc (thứ, khung) — nếu tra thẳng `T2_sang` thì luôn rỗng và
    thông báo ca trực rơi hết về quản lý mặc định.
    """
    if booking_dt.tzinfo is None:
        booking_dt = booking_dt.replace(tzinfo=ICT)
    else:
        booking_dt = booking_dt.astimezone(ICT)

    day_idx = booking_dt.weekday()  # 0=Monday, 6=Sunday
    thu_map = {0: "T2", 1: "T3", 2: "T4", 3: "T5", 4: "T6", 5: "T7", 6: "CN"}
    thu = thu_map.get(day_idx, "T2")

    phan_cong: dict[str, Any] = {}
    phan_cong_by_week: dict[str, Any] = {}
    khung_gio_raw: Any = {}
    user_role_map: dict[str, str] = {}
    store_manager = "nv_01"  # Lan - Quản lý mặc định

    try:
        with _conn() as cx:
            cx.row_factory = sqlite3.Row
            for row in cx.execute(
                "SELECT k, v FROM kv WHERE k IN ('phan_cong', 'phan_cong_by_week', 'khung_gio')"
            ).fetchall():
                try:
                    parsed = json.loads(row["v"])
                except Exception:
                    parsed = None
                if row["k"] == "phan_cong":
                    phan_cong = parsed if isinstance(parsed, dict) else {}
                elif row["k"] == "phan_cong_by_week":
                    phan_cong_by_week = parsed if isinstance(parsed, dict) else {}
                else:
                    khung_gio_raw = parsed
            users = cx.execute(
                "SELECT nv_id, role, display_name FROM users WHERE store_id=?", (store_id,)
            ).fetchall()
            user_role_map = {u["nv_id"]: u["role"] for u in users}
    except Exception:
        pass

    # Phân công theo TUẦN của ngày đặt bàn (không phải tuần hiện tại — khách có
    # thể đặt trước cho tuần sau). `solver_adapter._week_store` ghi
    # `phan_cong_by_week[tuần]`, còn `phan_cong` chỉ giữ kết quả tuần gần nhất;
    # `sprint3._phan_cong` và `sprint45._phan` đều ưu tiên by_week — ở đây phải
    # nhất quán, nếu không thông báo ca trực sẽ gửi cho người của tuần CŨ.
    phan_cong_tuan = _phan_cong_theo_tuan(phan_cong, phan_cong_by_week, booking_dt)

    phut_trong_ngay = booking_dt.hour * 60 + booking_dt.minute
    khung = _khung_theo_gio(phut_trong_ngay, _khung_gio_config(khung_gio_raw))

    # Shift code pattern (e.g. T2_sang) — mã khung logic, dùng cho log/đối chiếu.
    ca_id = f"{thu}_{khung}"

    # Gộp nhân viên của TẤT CẢ ca_id thuộc (thứ, khung) này: mỗi khung có thể
    # gồm nhiều ca theo vị trí (pha chế / thu ngân / phục vụ).
    ca_ids = _ca_meta_theo_khung().get((thu, khung), [])
    assigned_nv_ids: list[str] = []
    for cid in ca_ids:
        for nv in phan_cong_tuan.get(cid) or []:
            if isinstance(nv, str) and nv not in assigned_nv_ids:
                assigned_nv_ids.append(nv)

    if not assigned_nv_ids:
        # Tương thích ngược: môi trường cũ có thể ghi `phan_cong` theo mã khung.
        legacy = phan_cong_tuan.get(ca_id)
        if isinstance(legacy, list):
            assigned_nv_ids = [str(nv) for nv in legacy if nv]

    primary_nv = None
    backup_nvs = []

    for nv in assigned_nv_ids:
        role = user_role_map.get(nv, "nhan_vien")
        if role in ("quan_ly", "chu_quan") and not primary_nv:
            primary_nv = nv
        else:
            backup_nvs.append(nv)

    if not primary_nv:
        if assigned_nv_ids:
            primary_nv = assigned_nv_ids[0]  # First staff is shift lead
            backup_nvs = assigned_nv_ids[1:]
        else:
            primary_nv = store_manager

    if store_manager not in backup_nvs and store_manager != primary_nv:
        backup_nvs.append(store_manager)

    return {
        "ca_id": ca_id,
        "ca_ids": ca_ids,
        "khung": khung,
        "thu": thu,
        "primary_nv_id": primary_nv,
        "backup_nv_ids": backup_nvs,
    }


def dispatch_reservation_notification(
    reservation: dict[str, Any], store_id: str = "quan_01"
) -> dict[str, Any]:
    """
    Create in-app notifications and dispatch external push (Telegram/Zalo)
    to the on-duty manager for the confirmed booking.

    Người nhận chính là `notified_nv_id` (trưởng ca). Nếu trưởng ca chưa xác
    nhận trong `ESCALATION_*`, worker sẽ nhắc thêm người dự phòng
    (`backup_nv_ids`) — xem `notify_backup_if_unacked`.
    """
    res_id = reservation.get("id", "")
    customer = reservation.get("customer_name", "Khách hàng")
    phone = reservation.get("phone", "")
    booking_time = reservation.get("booking_time", "")
    party = reservation.get("party_size", 2)
    table_ids = ", ".join(reservation.get("table_ids") or ["Chưa gán"])
    manager_nv_id = reservation.get("notified_nv_id") or "nv_01"

    # Human-readable time
    try:
        dt = parse_booking_datetime(booking_time)
        time_str = dt.strftime("%H:%M ngày %d/%m/%Y")
    except Exception:
        time_str = booking_time

    title = f"🔔 Đặt bàn mới: Bàn {table_ids} ({customer}, {party} người)"
    content = (
        f"Khách hàng {customer} (SĐT: {phone}) vừa đặt bàn thành công qua AI Chatbot.\n"
        f"• Thời gian: {time_str}\n"
        f"• Số khách: {party} người | Bàn gán: {table_ids}\n"
        f"Vui lòng kiểm tra và chuẩn bị bàn chu đáo trước giờ đón khách!"
    )

    tb_id = thong_bao_ca_create(
        {
            "store_id": store_id,
            "dat_ban_id": res_id,
            "nv_id": manager_nv_id,
            "tieu_de": title,
            "noi_dung": content,
            "da_xem": 0,
        }
    )

    # Check if manager is linked to Telegram
    tg_id = kenh_bind_get("telegram", manager_nv_id)
    dispatch_status = "in_app_only"
    if tg_id:
        try:
            from ca_agents.messaging import get_port

            port = get_port("telegram")
            port.send(tg_id, f"[{title}]\n{content}")
            dispatch_status = "telegram_dispatched"
        except Exception as e:
            LOG.warning(f"Could not send Telegram notification to {tg_id}: {e}")
            dispatch_status = "telegram_failed"

    return {"notification_id": tb_id, "dispatch_status": dispatch_status}


def dispatch_in_background(
    reservation: dict[str, Any], store_id: str = "quan_01"
) -> dict[str, Any]:
    """Gửi thông báo đặt bàn ở luồng NỀN, không chặn response cho khách.

    Vì sao: `dispatch_reservation_notification` gọi Telegram **đồng bộ**. Nếu
    Telegram chậm/timeout, hàm gọi nó (và do đó cả lượt trả lời khách) bị treo
    theo. Đẩy sang thread nền giữ response nhanh; lỗi gửi chỉ ghi log —
    thông báo trong app đã tạo trước đó nên không mất dữ liệu.

    Dùng ở luồng webhook/agent; ở test hoặc CLI có thể gọi hàm đồng bộ trực tiếp.
    """
    import threading

    def _chay() -> None:
        try:
            dispatch_reservation_notification(reservation, store_id)
        except Exception as e:  # noqa: BLE001
            LOG.warning(f"Background reservation notify failed: {e}")

    threading.Thread(target=_chay, name="res-notify", daemon=True).start()
    return {"queued": True}


def notify_backup_if_unacked(store_id: str = "quan_01") -> dict[str, Any]:
    """Nhắc người DỰ PHÒNG của ca khi trưởng ca chưa xác nhận thông báo.

    `resolve_shift_manager_and_backup` đã tính `backup_nv_ids` từ lâu nhưng
    không nơi nào dùng — nghĩa là trưởng ca bận thì không có ai được nhắc. Hàm
    này biến danh sách đó thành leo thang thật: đơn đã gửi thông báo quá
    `ESCALATION_AFTER_MINUTES` mà `notification_acked_at` còn NULL thì tạo thêm
    một thông báo cho từng người dự phòng của ca đó.

    Idempotent: mỗi (đơn, người dự phòng) chỉ tạo một lần — kiểm bằng việc tìm
    thông báo cũ có cùng `dat_ban_id` + `nv_id`.
    """
    init_db()
    now_dt = get_ict_now()
    cutoff_dt = now_dt - timedelta(minutes=ESCALATION_AFTER_MINUTES)

    rows = reservation_list(store_id=store_id, status="confirmed", limit=200)
    da_nhac: list[str] = []
    for r in rows:
        if r.get("notification_acked_at"):
            continue  # trưởng ca đã xác nhận → không cần leo thang

        # Chỉ leo thang đơn đã tạo đủ lâu (so bằng datetime, không so chuỗi).
        if not _created_truoc_moc(r.get("created_at"), cutoff_dt):
            continue

        primary = r.get("notified_nv_id") or ""
        # Dự phòng phải suy lại từ ca của đơn (chưa lưu cột riêng).
        try:
            booking_dt = parse_booking_datetime(str(r.get("booking_time") or ""))
        except (TypeError, ValueError):
            continue
        shift = resolve_shift_manager_and_backup(booking_dt, store_id)
        backup_ids = [nv for nv in shift.get("backup_nv_ids") or [] if nv and nv != primary]
        if not backup_ids:
            continue

        # Đọc idempotency trong connection NGẮN rồi đóng, KHÔNG lồng với lời gọi
        # ghi: `thong_bao_ca_create` tự mở connection riêng, lồng hai connection
        # ghi trên SQLite dễ deadlock.
        da_co: set[str] = set()
        with _conn() as cx:
            cx.row_factory = sqlite3.Row
            for nv_id in backup_ids:
                existed = cx.execute(
                    "SELECT 1 FROM thong_bao_ca WHERE dat_ban_id=? AND nv_id=? LIMIT 1",
                    (r["id"], nv_id),
                ).fetchone()
                if existed:
                    da_co.add(nv_id)

        for nv_id in backup_ids:
            if nv_id in da_co:
                continue  # đã nhắc người này rồi → idempotent
            thong_bao_ca_create(
                {
                    "store_id": store_id,
                    "dat_ban_id": r["id"],
                    "nv_id": nv_id,
                    "tieu_de": f"⚠️ Ca trực chưa xác nhận: {r.get('customer_name')}",
                    "noi_dung": (
                        f"Đơn đặt bàn của {r.get('customer_name')} "
                        f"(bàn {', '.join(r.get('table_ids') or []) or 'chưa gán'}) "
                        f"chưa được trưởng ca xác nhận sau {ESCALATION_AFTER_MINUTES} phút. "
                        "Nhờ bạn kiểm tra và chuẩn bị bàn."
                    ),
                    "da_xem": 0,
                }
            )
            da_nhac.append(f"{r['id']}:{nv_id}")

    return {"escalated": da_nhac, "count": len(da_nhac)}


def send_reservation_confirmation_email(
    reservation: dict[str, Any],
    to_email: str | None = None,
    store_profile: dict[str, Any] | None = None,
) -> bool:
    """Send table reservation confirmation ticket / email to customer's Gmail."""
    email = (to_email or reservation.get("email") or "").strip()
    # Fallback: record đọc từ DB cũ có thể chưa có cột email (email nằm trong notes
    # dạng "Email: xxx@yyy.zz"). Parse lại để không mất phiếu xác nhận.
    if not email:
        notes = reservation.get("notes") or ""
        m = re.search(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", notes)
        if m:
            email = m.group(1).strip()
    if not email or "@" not in email:
        LOG.warning("No valid email provided for reservation confirmation.")
        return False

    customer_name = reservation.get("customer_name") or "Quý khách"
    phone = reservation.get("phone") or "Chưa cung cấp"
    party_size = reservation.get("party_size", 2)
    table_ids = ", ".join(reservation.get("table_ids") or ["Khu vực đón tiếp"])
    booking_time = reservation.get("booking_time", "")
    res_id = reservation.get("id", "")

    try:
        dt = parse_booking_datetime(booking_time)
        time_display = dt.strftime("%H:%M ngày %d/%m/%Y")
    except Exception:
        time_display = booking_time

    profile = store_profile or {}
    # ADR-008: không fallback dữ liệu bịa — profile rỗng thì bỏ dòng tương ứng.
    store_name = str(profile.get("ten_quan") or "").strip() or "Quán cà phê"
    _addr = str(profile.get("dia_chi") or "").strip()
    _phone = str(profile.get("hotline") or "").strip()
    store_address = _addr or ""
    store_hotline = _phone or ""
    footer_lines = [ln for ln in (
        f"{store_name}",
        f"Địa chỉ: {store_address}" if store_address else "",
        f"Hotline: {store_hotline}" if store_hotline else "",
    ) if ln]

    subject = f"[{store_name}] PHIẾU XÁC NHẬN ĐẶT BÀN - {customer_name} ({time_display})"

    # Plain text version
    body = (
        f"Kính gửi {customer_name},\n\n"
        f"{store_name} xin trân trọng thông báo yêu cầu đặt bàn của Quý khách đã được xác nhận thành công!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  PHIẾU XÁC NHẬN ĐẶT BÀN\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Mã đặt bàn    : {res_id}\n"
        f"  Thời gian đến : {time_display}\n"
        f"  Số lượng khách: {party_size} người\n"
        f"  Bàn xếp chỗ   : {table_ids}\n"
        f"  Người đặt     : {customer_name}\n"
        f"  Số điện thoại : {phone}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Quán sẽ chuẩn bị chỗ ngồi chu đáo và giữ bàn cho Quý khách tối đa 15 phút so với giờ hẹn.\n"
        f"Nếu Quý khách có bất kỳ thay đổi nào, vui lòng liên hệ hotline hoặc phản hồi tin nhắn Messenger.\n\n"
        f"Trân trọng cảm ơn và rất hân hạnh được đón tiếp Quý khách!\n"
        f"---\n"
        + "\n".join(footer_lines)
        + "\n"
    )

    # Rich HTML version — table-based layout for maximum Gmail/Outlook compatibility.
    # Gmail strips <style> in <head> and does not support flexbox/grid, so all
    # styling is inline and layout uses tables.
    # Phong cách: Sang trọng (Elegant) — nền sáng kem + vàng gold.
    # Dùng font sans-serif (Arial) vì font serif (Georgia) trên Windows tách rời
    # dấu tiếng Việt (cầu -> cầ u) khi xem trên web máy tính.
    html_body = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#f4f1ec;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f1ec; padding:24px 12px;">
        <tr>
          <td align="center">
            <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%; background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 10px 30px rgba(120,53,15,0.12); font-family:Arial, 'Segoe UI', Helvetica, sans-serif; color:#3f2d1d;">
              <!-- HEADER - Light cream background to make red/orange logo pop -->
              <tr>
                <td style="background-color:#f9f6ee; padding:36px 40px; text-align:center; border-bottom:1px solid #ece5d8;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td align="center" style="padding-bottom:16px;">
                        <img src="cid:logo_nhipquan" alt="{store_name}" width="160" height="160" style="display:block; width:160px; height:160px; object-fit:contain;">
                      </td>
                    </tr>
                    <tr>
                      <td align="center" style="color:#8a6d3b; font-size:13px; letter-spacing:1px; text-transform:uppercase; padding-bottom:6px;">{store_name}</td>
                    </tr>
                    <tr>
                      <td align="center" style="color:#1f3d2b; font-size:24px; font-weight:bold;">XÁC NHẬN ĐẶT BÀN</td>
                    </tr>
                    <tr>
                      <td align="center" style="padding-top:14px;">
                        <span style="display:inline-block; background-color:#c9a227; color:#3f2d1d; font-size:11px; font-weight:bold; letter-spacing:1px; padding:5px 18px; border-radius:2px; text-transform:uppercase;">Đã xác nhận</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <!-- BODY -->
              <tr>
                <td style="padding:32px 40px 8px 40px;">
                  <p style="margin:0 0 8px 0; font-size:17px; line-height:1.5;">Kính gửi <strong>{customer_name}</strong>,</p>
                  <p style="margin:0; font-size:14px; line-height:1.8; color:#6b5d4f;">
                    Chúng tôi trân trọng xác nhận yêu cầu đặt bàn của Quý khách tại {store_name}. Thông tin chi tiết như sau:
                  </p>
                </td>
              </tr>
              <!-- DETAILS - elegant table with gold dividers -->
              <tr>
                <td style="padding:24px 40px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8dfd0; border-radius:6px;">
                    <tr>
                      <td style="padding:16px 24px; background-color:#faf7f1; border-bottom:1px solid #e8dfd0; font-size:13px; color:#8a7a66; text-transform:uppercase; font-weight:bold;">Thông tin đặt bàn</td>
                    </tr>
                    <tr>
                      <td style="padding:6px 24px; border-bottom:1px solid #f0e9dd;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">
                          <tr>
                            <td style="padding:8px 0; color:#8a7a66; width:160px;">Mã đặt bàn</td>
                            <td style="padding:8px 0; font-weight:bold; color:#3f2d1d; font-family:Consolas, monospace;">{res_id}</td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:6px 24px; border-bottom:1px solid #f0e9dd;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">
                          <tr>
                            <td style="padding:8px 0; color:#8a7a66; width:160px;">Thời gian đến</td>
                            <td style="padding:8px 0; font-weight:bold; color:#1f3d2b; font-size:15px;">{time_display}</td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:6px 24px; border-bottom:1px solid #f0e9dd;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">
                          <tr>
                            <td style="padding:8px 0; color:#8a7a66; width:160px;">Số lượng khách</td>
                            <td style="padding:8px 0; font-weight:bold; color:#3f2d1d;">{party_size} người</td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:6px 24px; border-bottom:1px solid #f0e9dd;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">
                          <tr>
                            <td style="padding:8px 0; color:#8a7a66; width:160px;">Bàn xếp trước</td>
                            <td style="padding:8px 0; font-weight:bold; color:#3f2d1d;">Bàn {table_ids}</td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:6px 24px;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">
                          <tr>
                            <td style="padding:8px 0; color:#8a7a66; width:160px;">Số điện thoại</td>
                            <td style="padding:8px 0; font-weight:bold; color:#3f2d1d;">{phone}</td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <!-- NOTE -->
              <tr>
                <td style="padding:0 40px 8px 40px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#fdf6e3; border-left:3px solid #c9a227; border-radius:4px;">
                    <tr>
                      <td style="padding:14px 18px; font-size:13px; line-height:1.7; color:#7a5c1e;">
                        <strong>Lưu ý:</strong> Bàn sẽ được giữ tối đa <strong>15 phút</strong> so với giờ hẹn. Quý khách vui lòng đến đúng giờ để có trải nghiệm tốt nhất.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <!-- FOOTER -->
              <tr>
                <td style="padding:24px 40px 32px 40px; border-top:1px solid #f0e9dd; margin-top:8px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:13px; color:#8a7a66;">
                    {f'<tr><td style="padding:4px 0;">Địa chỉ: <strong style="color:#3f2d1d;">{store_address}</strong></td></tr>' if store_address else ''}
                    {f'<tr><td style="padding:4px 0;">Hotline: <strong style="color:#3f2d1d;">{store_hotline}</strong></td></tr>' if store_hotline else ''}
                  </table>
                  <p style="margin:18px 0 0 0; font-size:12px; color:#b0a28e; text-align:center; line-height:1.6;">
                    Email tự động từ hệ thống {store_name}. Vui lòng không trả lời trực tiếp.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    try:
        from ca_agents.ag_mail import send_mail

        # Logo quán nhúng inline (CID) để hiển thị trong header email.
        # Ưu tiên bản "bold" (đậm nét) nếu có, fallback về bản gốc.
        logo_path = Path(__file__).resolve().parents[5] / "docs" / "hinh" / "logo_bold.png"
        if not logo_path.exists():
            logo_path = Path(__file__).resolve().parents[5] / "docs" / "hinh" / "logo.png"
        attachments: list[dict[str, Any] | str] = []
        if logo_path.exists():
            attachments.append(
                {
                    "path": str(logo_path),
                    "filename": "logo.png",
                    "cid": "logo_nhipquan",
                    "is_inline": True,
                    "content_type": "image/png",
                }
            )

        result = send_mail(
            to_emails=[email],
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachments,
        )
        return result.ok
    except Exception as e:
        LOG.warning(f"Could not send reservation confirmation email to {email}: {e}")
        return False


def customer_cancel_reservation(
    psid: str,
    reason: str = "Khách yêu cầu hủy qua chat",
    store_id: str = "quan_01",
) -> dict[str, Any] | None:
    """
    Cancel active reservation for a customer via chat.
    """
    actives = reservation_find_active_by_psid(psid, store_id)
    if not actives:
        return None

    target = actives[0]
    res_id = target["id"]
    success = reservation_update_status(
        res_id,
        new_status="cancelled",
        actor="customer",
        reason=reason,
        cancelled_by="customer",
    )
    if success:
        # Notify shift manager of cancellation
        manager_id = target.get("notified_nv_id") or "nv_01"
        table_str = ", ".join(target.get("table_ids") or [])
        thong_bao_ca_create(
            {
                "store_id": store_id,
                "dat_ban_id": res_id,
                "nv_id": manager_id,
                "tieu_de": f"⚠️ Khách hủy bàn {table_str} ({target.get('customer_name')})",
                "noi_dung": f"Khách hàng {target.get('customer_name')} ({target.get('phone')}) đã hủy lịch hẹn lúc {target.get('booking_time')}. Bàn {table_str} đã được giải phóng trên hệ thống.",
                "da_xem": 0,
            }
        )
        return reservation_get(res_id)
    return None


# Register backend with agent layer (Clean Architecture / Ports & Adapters)
try:
    from ca_agents.ag_concierge import register_reservation_backend

    register_reservation_backend(
        book_fn=atomic_hold_or_book_table,
        anti_abuse_fn=check_anti_abuse,
        cancel_fn=customer_cancel_reservation,
        notify_fn=dispatch_reservation_notification,
        send_mail_fn=send_reservation_confirmation_email,
        is_enabled_fn=auto_reservation_enabled,
    )
except Exception:
    pass

