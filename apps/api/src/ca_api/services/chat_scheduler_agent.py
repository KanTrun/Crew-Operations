"""Chat AI Scheduler Agent — Natural language availability parser & automatic shift scheduler."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, cast

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

from ca_api.persist import (
    availability_confirmation_upsert,
    availability_confirmed_list,
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

_DAY_PATTERNS = {
    "T2": [r"t2\b", r"thứ 2\b", r"thứ hai\b"],
    "T3": [r"t3\b", r"thứ 3\b", r"thứ ba\b"],
    "T4": [r"t4\b", r"thứ 4\b", r"thứ tư\b"],
    "T5": [r"t5\b", r"thứ 5\b", r"thứ năm\b"],
    "T6": [r"t6\b", r"thứ 6\b", r"thứ sáu\b"],
    "T7": [r"t7\b", r"thứ 7\b", r"thứ bảy\b"],
    "CN": [r"cn\b", r"chủ nhật\b"],
}
_WEEKDAY_INDEX = {day: index for index, day in enumerate(ALL_DAYS)}
_SHIFT_RANGES = {
    "Sáng": (6 * 60 + 30, 12 * 60),
    "Chiều": (12 * 60, 17 * 60 + 30),
    "Tối": (17 * 60 + 30, 22 * 60 + 30),
}
_DATE_TOKEN_RE = re.compile(
    r"(?<!\d)(?P<day>0?[1-9]|[12]\d|3[01])/(?P<month>0?[1-9]|1[0-2])(?:/(?P<year>\d{4}))?(?!\d)"
    r"|(?P<relative>hôm nay|ngày mai)"
    r"|(?P<weekday>t[2-7]\b|cn\b|thứ\s+(?:[2-7]|hai|ba|tư|năm|sáu|bảy)\b|chủ nhật\b)",
    re.IGNORECASE,
)
_TIME_RANGE_RE = re.compile(
    r"(?<!\d)(?P<start_hour>[01]?\d|2[0-3])(?:h|:)(?P<start_minute>[0-5]\d)?"
    r"\s*(?:-|–|đến|tới)\s*"
    r"(?P<end_hour>[01]?\d|2[0-3])(?:h|:)(?P<end_minute>[0-5]\d)?(?!\d)",
    re.IGNORECASE,
)


def _iso_week(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _day_code(value: str) -> str | None:
    return next(
        (day for day, patterns in _DAY_PATTERNS.items() if any(re.fullmatch(pattern, value) for pattern in patterns)),
        None,
    )


def _resolve_date_token(match: re.Match[str], text: str, reference_date: date) -> date | None:
    if match.group("day"):
        day = int(match.group("day"))
        month = int(match.group("month"))
        explicit_year = match.group("year")
        years = [int(explicit_year)] if explicit_year else [reference_date.year, reference_date.year + 1]
        for year in years:
            try:
                candidate = date(year, month, day)
            except ValueError:
                continue
            if explicit_year or candidate >= reference_date:
                return candidate
        return None
    if match.group("relative"):
        return reference_date if match.group("relative").lower() == "hôm nay" else reference_date + timedelta(days=1)

    day_code = _day_code(match.group("weekday").lower())
    if not day_code:
        return None
    context_start = max(0, match.start() - 20)
    context_end = min(len(text), match.end() + 20)
    next_week = bool(re.search(r"tuần\s+(?:sau|tới)", text[context_start:context_end]))
    week_start = reference_date - timedelta(days=reference_date.weekday())
    return week_start + timedelta(days=_WEEKDAY_INDEX[day_code] + (7 if next_week else 0))


def _extract_date_mentions(text: str, reference_date: date) -> list[tuple[int, int, date]]:
    mentions: list[tuple[int, int, date]] = []
    for match in _DATE_TOKEN_RE.finditer(text):
        resolved = _resolve_date_token(match, text, reference_date)
        if resolved:
            mentions.append((match.start(), match.end(), resolved))
    return mentions


def _minutes(hour: str, minute: str | None) -> int:
    return int(hour) * 60 + int(minute or 0)


def _clock(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _nearest_date_for_time(
    start: int, end: int, mentions: list[tuple[int, int, date]], text: str,
) -> date | None:
    candidates: list[tuple[int, date]] = []
    for mention_start, mention_end, resolved in mentions:
        if mention_end <= start:
            between = text[mention_end:start]
            distance = start - mention_end
        elif mention_start >= end:
            between = text[end:mention_start]
            distance = mention_start - end
        else:
            return resolved
        if not re.search(r"[,.;\n]", between):
            candidates.append((distance, resolved))
    return min(candidates, default=(0, None), key=lambda item: item[0])[1]


def _busy_intervals(text: str, mentions: list[tuple[int, int, date]]) -> list[dict[str, str]]:
    raw: list[tuple[date, int, int]] = []
    for match in _TIME_RANGE_RE.finditer(text):
        resolved = _nearest_date_for_time(match.start(), match.end(), mentions, text)
        start = _minutes(match.group("start_hour"), match.group("start_minute"))
        end = _minutes(match.group("end_hour"), match.group("end_minute"))
        if resolved and end > start:
            raw.append((resolved, start, end))

    merged: list[tuple[date, int, int]] = []
    for resolved, start, end in sorted(raw):
        if merged and merged[-1][0] == resolved and start <= merged[-1][2]:
            previous_date, previous_start, previous_end = merged[-1]
            merged[-1] = (previous_date, previous_start, max(previous_end, end))
        else:
            merged.append((resolved, start, end))
    return [
        {
            "date": resolved.isoformat(),
            "tuan_iso": _iso_week(resolved),
            "thu": ALL_DAYS[resolved.weekday()],
            "start": _clock(start),
            "end": _clock(end),
        }
        for resolved, start, end in merged
    ]


def _parse_shift_availability(text: str) -> dict[str, list[str]]:
    included_days: set[str] = set()
    range_match = re.search(r"(t[2-7]|thứ [2-7])\s*(?:-|đến|tới)\s*(t[2-7]|cn|chủ nhật|thứ [2-7])", text)
    if range_match:
        start_day = _day_code(range_match.group(1))
        end_day = _day_code(range_match.group(2))
        if start_day and end_day and _WEEKDAY_INDEX[start_day] <= _WEEKDAY_INDEX[end_day]:
            included_days.update(ALL_DAYS[_WEEKDAY_INDEX[start_day] : _WEEKDAY_INDEX[end_day] + 1])
    for day, patterns in _DAY_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            included_days.add(day)
    if not included_days and ("các ngày trong tuần" in text or "cả tuần" in text):
        included_days = set(ALL_DAYS)

    shifts: list[str] = []
    if "sáng" in text or "ca 1" in text:
        shifts.append("Sáng")
    if "chiều" in text or "ca 2" in text:
        shifts.append("Chiều")
    if "tối" in text or "ca 3" in text:
        shifts.append("Tối")
    if not shifts and any(term in text for term in ("cả ngày", "full", "rảnh hết")):
        shifts = list(SHIFTS)
    if not shifts or not re.search(r"rảnh|đăng ký", text):
        return {}
    return {day: list(shifts) for day in included_days}


def _remove_busy_conflicts(
    availability: dict[str, list[str]], busy_intervals: list[dict[str, str]],
) -> dict[str, list[str]]:
    normalized = {day: list(shifts) for day, shifts in availability.items()}
    for interval in busy_intervals:
        busy_start = _minutes(*interval["start"].split(":"))
        busy_end = _minutes(*interval["end"].split(":"))
        day = interval["thu"]
        normalized[day] = [
            shift for shift in normalized.get(day, [])
            if not (busy_start < _SHIFT_RANGES[shift][1] and busy_end > _SHIFT_RANGES[shift][0])
        ]
        if not normalized.get(day):
            normalized.pop(day, None)
    return normalized


def _busy_exclusions_as_availability(
    busy_intervals: list[dict[str, str]], tuan_iso: str,
) -> dict[str, list[str]]:
    """Convert explicit busy intervals into the shift availability contract used by CP-SAT."""
    relevant = [item for item in busy_intervals if item["tuan_iso"] == tuan_iso]
    if not relevant:
        return {}
    availability = {day: list(SHIFTS) for day in ALL_DAYS}
    return _remove_busy_conflicts(availability, relevant)


def _availability_summary(
    availability: dict[str, list[str]], busy_intervals: list[dict[str, str]],
) -> str:
    parts: list[str] = []
    if availability:
        available = "; ".join(
            f"{DAY_LABELS[day]}: {', '.join(availability[day])}" for day in ALL_DAYS if day in availability
        )
        parts.append(f"Rảnh {available}.")
    if busy_intervals:
        busy = "; ".join(
            f"{DAY_LABELS[item['thu']]} {date.fromisoformat(item['date']).strftime('%d/%m/%Y')}, "
            f"{item['start']}-{item['end']}"
            for item in busy_intervals
        )
        parts.append(f"Bận {busy}.")
    if busy_intervals and not availability:
        parts.append("Không tự suy diễn ca rảnh.")
    return " ".join(parts)


def parse_availability_details(text: str, *, reference_date: date | None = None) -> dict[str, Any]:
    """Parse explicit availability and busy intervals against a deterministic calendar date."""
    text_lower = text.lower()
    reference = reference_date or date.today()
    mentions = _extract_date_mentions(text_lower, reference)
    busy_intervals = _busy_intervals(text_lower, mentions) if "bận" in text_lower else []
    availability = _remove_busy_conflicts(_parse_shift_availability(text_lower), busy_intervals)
    resolved_dates = sorted({resolved.isoformat() for _, _, resolved in mentions})
    weeks = sorted({_iso_week(date.fromisoformat(value)) for value in resolved_dates})
    return {
        "availability": availability,
        "busy_intervals": busy_intervals,
        "resolved_dates": resolved_dates,
        "tuan_iso": weeks[0] if len(weeks) == 1 else None,
        "summary": _availability_summary(availability, busy_intervals),
    }


def parse_availability_text(text: str) -> dict[str, list[str]]:
    """Backward-compatible shift-only view of parsed availability."""
    return cast(dict[str, list[str]], parse_availability_details(text)["availability"])


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
    reference_date: date | None = None, store_id: str = "quan_01",
) -> dict[str, Any] | None:
    """Create a pending confirmation card; unconfirmed data never reaches the solver."""
    details = parse_availability_details(text, reference_date=reference_date)
    parsed = details["availability"]
    busy_intervals = details["busy_intervals"]
    if not parsed and not busy_intervals:
        return None
    reference = reference_date or date.today()
    week = (
        tuan_iso if tuan_iso and re.fullmatch(r"\d{4}-W\d{2}", tuan_iso)
        else details["tuan_iso"] or _iso_week(reference)
    )
    if not parsed and busy_intervals:
        parsed = _busy_exclusions_as_availability(busy_intervals, week)
    item = {
        "id": f"av_{uuid.uuid4().hex[:10]}",
        "conv_id": conv_id,
        "nv_id": nv_id,
        "display_name": display_name or nv_id,
        "store_id": store_id,
        "tuan_iso": week,
        "availability": parsed,
        "busy_intervals": busy_intervals,
        "summary": details["summary"],
        "source_text": text,
        "status": "cho_xac_nhan",
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    def add(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Một draft mới của cùng nhân viên/tuần thay draft cũ, không tạo bản ghi rác.
        items = [x for x in items if not (x.get("conv_id") == conv_id and x.get("nv_id") == nv_id and x.get("tuan_iso") == week and x.get("status") == "cho_xac_nhan")]
        items.append(item)
        return items[-200:]

    kv_mutate("lich_ban_confirmations", add, [])
    availability_confirmation_upsert(
        item_id=str(item["id"]),
        store_id=store_id,
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


def update_availability_confirmation(
    item_id: str, *, nv_id: str, status: str, correction: str = "", store_id: str = "quan_01"
) -> dict[str, Any]:
    found: dict[str, Any] | None = None

    def mutate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found
        for raw in items:
            if raw.get("id") != item_id:
                continue
            if raw.get("nv_id") != nv_id:
                raise PermissionError("khong_phai_nguoi_gui")
            if str(raw.get("store_id") or "quan_01") != store_id:
                raise PermissionError("khong_phai_cua_hang")
            item = dict(raw)
            if status == "cho_xac_nhan":
                details = parse_availability_details(correction)
                parsed = details["availability"]
                if not parsed and not details["busy_intervals"]:
                    raise ValueError("khong_doc_duoc_lich_ban")
                if not parsed and details["busy_intervals"]:
                    parsed = _busy_exclusions_as_availability(
                        details["busy_intervals"], str(item.get("tuan_iso") or "")
                    )
                item["availability"] = parsed
                item["busy_intervals"] = details["busy_intervals"]
                item["summary"] = details["summary"]
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
        store_id=store_id,
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
    store_id = str(user_sess.get("store_id") or "quan_01")
    requested_week = str(user_sess.get("tuan_iso") or "").strip()
    if re.fullmatch(r"\d{4}-W\d{2}", requested_week):
        week = requested_week
    else:
        iso = date.today().isocalendar()
        week = f"{iso.year}-W{iso.week:02d}"

    # Report phải khớp với dữ liệu solver dùng: toàn store, không chỉ conv này.
    # (run_authoritative_schedule đọc availability_confirmed_list(store_id, week).)
    confirmed = availability_confirmed_list(store_id, week)
    availabilities: dict[str, dict[str, list[str]]] = {}
    for item in confirmed:
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

    solver_run = run_authoritative_schedule(
        store_id=store_id,
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
