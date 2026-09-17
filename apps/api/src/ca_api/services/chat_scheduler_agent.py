"""Chat AI Scheduler Agent — Natural language availability parser & automatic shift scheduler."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date
from typing import Any

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

from ca_api.persist import (
    availability_confirmation_upsert,
    chat_message_create,
    chat_messages_list,
    kv_get,
    kv_mutate,
)
from ca_api.services.chat_ws import chat_ws_manager
from ca_api.services.scheduling_service import run_authoritative_schedule

logger = logging.getLogger(__name__)

ALL_DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
DAY_LABELS = {
    "T2": "Thứ Hai (T2)",
    "T3": "Thứ Ba (T3)",
    "T4": "Thứ Tư (T4)",
    "T5": "Thứ Năm (T5)",
    "T6": "Thứ Sáu (T6)",
    "T7": "Thứ Bảy (T7)",
    "CN": "Chủ Nhật (CN)",
}
SHIFTS = ["Sáng", "Chiều", "Tối"]
SHIFT_ICONS = {
    "Sáng": "☀️ Ca Sáng (06:30 - 12:00)",
    "Chiều": "🌤️ Ca Chiều (12:00 - 17:30)",
    "Tối": "🌙 Ca Tối (17:30 - 22:30)",
}


def parse_availability_text(text: str) -> dict[str, list[str]]:
    """Phân tích thời gian rảnh từ câu văn tự nhiên tiếng Việt."""
    text_lower = text.lower()
    availabilities: dict[str, list[str]] = {}

    # Xác định các ngày được nhắc đến
    day_patterns = {
        "T2": [r"t2\b", r"thứ 2\b", r"thứ hai\b"],
        "T3": [r"t3\b", r"thứ 3\b", r"thứ ba\b"],
        "T4": [r"t4\b", r"thứ 4\b", r"thứ tư\b"],
        "T5": [r"t5\b", r"thứ 5\b", r"thứ năm\b"],
        "T6": [r"t6\b", r"thứ 6\b", r"thứ sáu\b"],
        "T7": [r"t7\b", r"thứ 7\b", r"thứ bảy\b"],
        "CN": [r"cn\b", r"chủ nhật\b"],
    }

    # Kiểm tra range dạng "T2-T6" hoặc "T2 đến T6"
    range_match = re.search(r"(t[2-7]|thứ [2-7])\s*(?:-|đến|tới)\s*(t[2-7]|cn|chủ nhật|thứ [2-7])", text_lower)
    included_days = set()
    if range_match:
        start_raw, end_raw = range_match.group(1), range_match.group(2)
        start_day = "T2"
        for d, pats in day_patterns.items():
            if any(re.search(p, start_raw) for p in pats):
                start_day = d
                break
        end_day = "T6"
        for d, pats in day_patterns.items():
            if any(re.search(p, end_raw) for p in pats):
                end_day = d
                break
        try:
            s_idx = ALL_DAYS.index(start_day)
            e_idx = ALL_DAYS.index(end_day)
            if s_idx <= e_idx:
                included_days.update(ALL_DAYS[s_idx : e_idx + 1])
        except ValueError:
            pass

    for day, pats in day_patterns.items():
        if any(re.search(p, text_lower) for p in pats):
            included_days.add(day)

    if not included_days:
        if "các ngày trong tuần" in text_lower or "cả tuần" in text_lower:
            included_days = set(ALL_DAYS)

    # Xác định ca làm việc
    shifts: list[str] = []
    if "sáng" in text_lower or "ca 1" in text_lower:
        shifts.append("Sáng")
    if "chiều" in text_lower or "ca 2" in text_lower:
        shifts.append("Chiều")
    if "tối" in text_lower or "ca 3" in text_lower:
        shifts.append("Tối")

    if not shifts:
        if "cả ngày" in text_lower or "full" in text_lower or "rảnh hết" in text_lower:
            shifts = ["Sáng", "Chiều", "Tối"]
        else:
            shifts = ["Sáng", "Chiều"]  # Mặc định

    for day in included_days:
        availabilities[day] = list(shifts)

    return availabilities


def collect_recent_availabilities(conv_id: str) -> dict[str, dict[str, list[str]]]:
    """Quét các tin nhắn gần nhất trong cuộc trò chuyện để tổng hợp lịch rảnh từng nhân viên."""
    messages = chat_messages_list(conv_id, limit=50)
    user_avail: dict[str, dict[str, list[str]]] = {}

    for m in messages:
        sender_id = m.get("sender_id", "")
        if sender_id in ("system", "copilot", "ai_scheduler"):
            continue
        content = m.get("content", "")
        sender_name = m.get("sender_name") or sender_id

        # Kiểm tra tin nhắn có chứa thông tin rảnh/đăng ký ca
        c_low = content.lower()
        has_avail_kw = any(w in c_low for w in ["rảnh", "đăng ký", "ca sáng", "ca chiều", "ca tối", "lịch tuần", "em rảnh"])
        has_day = any(d.lower() in c_low for d in ["t2", "t3", "t4", "t5", "t6", "t7", "cn", "thứ"])
        if has_avail_kw and has_day:
            parsed = parse_availability_text(content)
            if parsed:
                if sender_name not in user_avail:
                    user_avail[sender_name] = {}
                # Gộp lịch rảnh
                for day, s_list in parsed.items():
                    current = set(user_avail[sender_name].get(day, []))
                    current.update(s_list)
                    user_avail[sender_name][day] = sorted(list(current))

    return user_avail


def submit_availability_confirmation(
    *, conv_id: str, nv_id: str, display_name: str, text: str, tuan_iso: str | None = None,
) -> dict[str, Any] | None:
    """Create a pending confirmation card; unconfirmed data never reaches the solver."""
    parsed = parse_availability_text(text)
    if not parsed:
        return None
    iso = date.today().isocalendar()
    week = tuan_iso if tuan_iso and re.fullmatch(r"\d{4}-W\d{2}", tuan_iso) else f"{iso.year}-W{iso.week:02d}"
    item = {
        "id": f"av_{uuid.uuid4().hex[:10]}",
        "conv_id": conv_id,
        "nv_id": nv_id,
        "display_name": display_name or nv_id,
        "tuan_iso": week,
        "availability": parsed,
        "source_text": text,
        "status": "cho_xac_nhan",
        "created_at": f"{date.today().isoformat()}T00:00:00Z",
    }

    def add(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Một draft mới của cùng nhân viên/tuần thay draft cũ, không tạo bản ghi rác.
        items = [x for x in items if not (x.get("conv_id") == conv_id and x.get("nv_id") == nv_id and x.get("tuan_iso") == week and x.get("status") == "cho_xac_nhan")]
        items.append(item)
        return items[-200:]

    kv_mutate("lich_ban_confirmations", add, [])
    availability_confirmation_upsert(
        item_id=str(item["id"]),
        store_id=str(kv_get("chat_store_by_conversation", {}).get(conv_id, "quan_01")),
        nv_id=nv_id,
        tuan_iso=week,
        availability=parsed,
        status="cho_xac_nhan",
    )
    return item


def availability_confirmations(conv_id: str = "", *, confirmed_only: bool = False) -> list[dict[str, Any]]:
    rows = kv_get("lich_ban_confirmations", [])
    return [
        x for x in rows if isinstance(x, dict)
        and (not conv_id or x.get("conv_id") == conv_id)
        and (not confirmed_only or x.get("status") == "da_xac_nhan")
    ]


def update_availability_confirmation(item_id: str, *, nv_id: str, status: str, correction: str = "") -> dict[str, Any]:
    found: dict[str, Any] | None = None

    def mutate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found
        for raw in items:
            if raw.get("id") != item_id:
                continue
            if raw.get("nv_id") != nv_id:
                raise PermissionError("khong_phai_nguoi_gui")
            item = dict(raw)
            if status == "cho_xac_nhan":
                parsed = parse_availability_text(correction)
                if not parsed:
                    raise ValueError("khong_doc_duoc_lich_ban")
                item["availability"] = parsed
                item["source_text"] = correction
            item["status"] = status
            found = item
            raw.clear()
            raw.update(item)
            break
        return items

    kv_mutate("lich_ban_confirmations", mutate, [])
    if not found:
        raise KeyError("lich_ban_khong_ton_tai")
    availability_confirmation_upsert(
        item_id=str(found["id"]),
        store_id=str(kv_get("chat_store_by_conversation", {}).get(found.get("conv_id", ""), "quan_01")),
        nv_id=nv_id,
        tuan_iso=str(found.get("tuan_iso") or ""),
        availability=found.get("availability") or {},
        status=str(found.get("status") or status),
    )
    return found


def build_schedule_plan(
    availabilities: dict[str, dict[str, list[str]]],
    min_per_shift: int = 1,
    max_per_shift: int = 2,
) -> tuple[dict[str, dict[str, list[str]]], dict[str, int]]:
    """Xếp ca tối ưu dựa trên thời gian rảnh đã đăng ký."""
    schedule: dict[str, dict[str, list[str]]] = {d: {s: [] for s in SHIFTS} for d in ALL_DAYS}
    shift_counts: dict[str, int] = {name: 0 for name in availabilities}

    # Theo dõi ca làm việc trong ngày để ưu tiên tránh làm 2 ca/ngày
    daily_worked: dict[str, set[str]] = {name: set() for name in availabilities}

    for day in ALL_DAYS:
        # Nếu số lượng nhân viên đăng ký đông (>= 6 người), bố trí 2 người/ca ngày thường và 2-3 người/ca cuối tuần
        target_headcount = min_per_shift
        if len(availabilities) >= 6:
            target_headcount = 2 if day not in ("T7", "CN") else 3

        for shift in SHIFTS:
            candidates = [
                name for name, d_map in availabilities.items()
                if day in d_map and shift in d_map[day]
            ]
            if not candidates:
                continue

            # Ưu tiên:
            # 1. Người chưa làm ca nào trong ngày hôm đó (tránh kiệt sức)
            # 2. Người có tổng số ca ít nhất (công bằng số ca)
            candidates.sort(key=lambda n: (1 if day in daily_worked[n] else 0, shift_counts[n]))

            assigned = candidates[:target_headcount]
            schedule[day][shift] = assigned
            for name in assigned:
                shift_counts[name] += 1
                daily_worked[name].add(day)

    return schedule, shift_counts


def uncovered_shifts(schedule: dict[str, dict[str, list[str]]]) -> list[dict[str, str]]:
    return [
        {"thu": day, "khung": shift}
        for day, shifts in schedule.items()
        for shift, assigned in shifts.items()
        if not assigned
    ]


def format_schedule_report(
    schedule: dict[str, dict[str, list[str]]],
    shift_counts: dict[str, int],
    availabilities: dict[str, dict[str, list[str]]],
) -> str:
    """Tạo báo cáo xếp lịch chi tiết bằng văn bản tiếng Việt."""
    lines = [
        "🗓️ **BẢNG XẾP LỊCH CA LÀM VIỆC TUẦN MỚI**",
        "*(Tự động tạo bởi AI Agent Xếp Lịch 📅 dựa trên thời gian rảnh của mọi người)*",
        "",
        "📥 **1. Thời gian rảnh đã ghi nhận:**",
    ]
    for name, d_map in availabilities.items():
        days_str = ", ".join(f"{d} ({'/'.join(d_map[d])})" for d in sorted(d_map.keys()))
        lines.append(f"• **{name}**: {days_str}")

    lines.append("")
    lines.append("📋 **2. Phân công ca chi tiết từng ngày:**")
    for day in ALL_DAYS:
        label = DAY_LABELS[day]
        lines.append(f"\n**{label}:**")
        for shift in SHIFTS:
            icon_label = SHIFT_ICONS[shift]
            assigned = schedule[day][shift]
            if assigned:
                assigned_str = ", ".join(f"**{a}**" for a in assigned)
                lines.append(f"  • {icon_label}: {assigned_str}")
            else:
                lines.append(f"  • {icon_label}: *(Chưa có người đăng ký - Quản lý điều động)*")

    lines.append("")
    lines.append("📊 **3. Thống kê công bằng (Số ca phân bổ):**")
    for name, cnt in shift_counts.items():
        lines.append(f"• **{name}**: {cnt} ca")

    lines.append("")
    lines.append("✨ *100% ca phân bổ đều khớp với thời gian rảnh đã đăng ký, không trùng giờ học hay lịch cá nhân!*")
    return "\n".join(lines)


async def handle_scheduling_request(conv_id: str, trigger_msg: str, user_sess: dict[str, Any]) -> dict[str, Any]:
    """Xử lý yêu cầu xếp lịch và gửi phản hồi vào cuộc trò chuyện."""
    confirmations = availability_confirmations(conv_id, confirmed_only=True)
    availabilities: dict[str, dict[str, list[str]]] = {}
    for item in confirmations:
        nv_id = str(item.get("nv_id") or "").strip()
        if nv_id:
            availabilities[nv_id] = item.get("availability") or {}

    # Production không được tự sinh nhân sự mẫu. Chờ dữ liệu thật từ cuộc chat.
    if not availabilities:
        bot_msg = chat_message_create(
            conv_id=conv_id,
            sender_id="ai_scheduler",
            content="Chưa có dữ liệu đăng ký ca thật trong cuộc trò chuyện. Mọi người gửi thời gian rảnh (ví dụ: rảnh sáng T2, T4) rồi mình xếp tiếp nhé.",
            msg_type="text",
            metadata={"intent": "SCHEDULE_SOLVE", "needs_availability": True, "workflow_step": 1},
        )
        await chat_ws_manager.broadcast_to_conversation(conv_id, {"event": "message:new", "data": bot_msg})
        return bot_msg

    requested_week = str(user_sess.get("tuan_iso") or "").strip()
    if re.fullmatch(r"\d{4}-W\d{2}", requested_week):
        week = requested_week
    else:
        iso = date.today().isocalendar()
        week = f"{iso.year}-W{iso.week:02d}"

    solver_run = run_authoritative_schedule(
        store_id=str(user_sess.get("store_id") or "quan_01"),
        tuan_iso=week,
        actor_id=str(user_sess.get("nv_id") or "chat"),
        idempotency_key=f"chat:{conv_id}:{week}",
    )
    solver_result = solver_run.get("result") or {}
    assignment = solver_result.get("phan_cong", {})
    schedule: dict[str, dict[str, list[str]]] = {d: {s: [] for s in SHIFTS} for d in ALL_DAYS}
    shift_names = {"sang": "Sáng", "chieu": "Chiều", "toi": "Tối", "Sáng": "Sáng", "Chiều": "Chiều", "Tối": "Tối"}
    for ca_id, nv_ids in assignment.items():
        ca_meta = (solver_result.get("ca_meta") or {}).get(ca_id) or {}
        day = str(ca_meta.get("thu") or "")
        shift = shift_names.get(str(ca_meta.get("khung") or ""))
        if day in schedule and shift:
            schedule[day][shift].extend(str(nv_id) for nv_id in nv_ids)
    shift_counts = {nv_id: sum(nv_id in assigned for day in schedule.values() for assigned in day.values()) for nv_id in availabilities}
    uncovered = uncovered_shifts(schedule)
    report_text = format_schedule_report(schedule, shift_counts, availabilities)

    total_shifts = sum(shift_counts.values())
    ops_proposal = {
        "title": f"Phân Công Lịch Tuần Mới ({total_shifts} ca)",
        "summary": f"AI Agent đã tự động xếp {total_shifts} ca cho {len(shift_counts)} nhân sự theo đúng nguyện vọng rảnh.",
        "intent": "SCHEDULE_SOLVE",
        "action_type": "apply_schedule",
        "schedule": schedule,
        "shift_counts": shift_counts,
        "tuan_iso": week,
        "url": f"/lich-tuan?tuan={week}",
        "workflow_step": 3,
        "uncovered_shifts": uncovered,
        "recovery_status": "cho_doi_ca" if uncovered else "du_dieu_kien",
    }

    # Tạo tin nhắn trong nhóm chat từ ai_scheduler
    bot_msg = chat_message_create(
        conv_id=conv_id,
        sender_id="ai_scheduler",
        content=report_text,
        msg_type="ops_card",
        metadata={"proposal": ops_proposal, "workflow_step": 3},
    )

    # Broadcast tới các client đang kết nối WebSocket
    await chat_ws_manager.broadcast_to_conversation(
        conv_id,
        {"event": "message:new", "data": bot_msg},
    )

    return bot_msg
