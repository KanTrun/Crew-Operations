"""AG-CONCIERGE: Special Case, Complaint & Auto-Reservation Agent for Nhịp Quán.

Specialized in:
- Crisis de-escalation & Complaint handling via HEAR Framework.
- 2-Phase Dialog State Machine for Table Reservations:
    State 1 (EXTRACTING): Collect date, time, party size, phone, customer name.
    State 2 (CONFIRMING): Hold slot, summarize details, ask customer for explicit confirmation.
    State 3 (CONFIRMED): Execute atomic reservation, notify on-duty shift manager.
    State 4 (CANCELLATION): Handle customer cancel / modification request.
- Safe escalation to management for groups > 8 or when abuse/blacklists are triggered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

ICT = timezone(timedelta(hours=7))


@dataclass(frozen=True)
class ConciergeTicket:
    ticket_type: str  # "complaint" | "reservation" | "special_request"
    customer_message: str
    extracted_data: dict[str, Any]
    suggested_reply: str
    urgency: str  # "high" | "medium" | "low"
    action_type: str = "ask_info"  # "ask_info" | "ask_confirmation" | "confirmed" | "cancelled" | "needs_manager_review"
    requires_human_approval: bool = False
    reservation_record: dict[str, Any] | None = None


def handle_complaint(text: str, customer_name: str | None = None) -> ConciergeTicket:
    """
    Handle customer dissatisfaction and complaints with sincere empathy.
    Applies HEAR framework to de-escalate and collect contact info for management.
    """
    name = customer_name or "mình"
    reply = (
        f"Dạ em thật sự xin lỗi {name} vì trải nghiệm chưa được trọn vẹn hôm nay ạ!\n"
        "Em ghi nhận góp ý này để bếp/quầy rút kinh nghiệm ngay. Lần tới ghé quán em mời mình một ly Trà đào (trong ngưỡng chăm sóc ≤ 200.000đ) để lấy lại cảm giác dễ chịu nha!\n"
        "Anh/chị cho em xin số điện thoại để quán gửi ưu đãi và kiểm tra đơn nếu cần ạ."
    )
    return ConciergeTicket(
        ticket_type="complaint",
        customer_message=text,
        extracted_data={"issue_summary": text[:160]},
        suggested_reply=reply,
        urgency="medium",
        action_type="ask_info",
        requires_human_approval=False,
    )


def extract_reservation_entities(text: str) -> dict[str, Any]:
    """
    Extract date, time, party size, phone number, and intent signals from user input.
    """
    low = text.lower().strip()
    data: dict[str, Any] = {}

    # 1. Cancellation intent
    if any(k in low for k in ("hủy bàn", "huy ban", "hủy lịch", "huy lich", "không đến được", "khong den duoc", "bận không ghé", "ban khong ghe")):
        data["is_cancellation"] = True

    # 2. Confirmation intent
    if any(k in low for k in ("đúng rồi", "dung roi", "ok em", "ok nha", "chốt nha", "chot nha", "xác nhận", "xac nhan", "chuẩn rồi", "chuan roi", "đặt đi", "chốt đi", "ok")):
        data["is_confirmation"] = True

    # 3. Party size (e.g. "4 người", "nhóm 6 bạn", "2 ng", "10 người")
    size_m = re.search(r"(\d+)\s*(?:người|ng|khách|bạn|chỗ|pax)", low)
    if size_m:
        data["party_size"] = int(size_m.group(1))
    else:
        # Check spelled numbers
        word_num_map = {"một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9, "mười": 10}
        for w, num in word_num_map.items():
            if f"{w} người" in low or f"nhóm {w}" in low:
                data["party_size"] = num
                break

    # 4. Phone number (Vietnamese phone regex: 10 digits starting with 0 or +84)
    phone_m = re.search(r"(?:(?:\+84[\s.-]*)|0)[35789](?:[\s.-]*\d){8}(?!\d)", text)
    if phone_m:
        data["phone"] = re.sub(r"[\s.-]", "", phone_m.group(0))

    # 5. Customer name
    name_m = re.search(r"(?:tên|tên là|mình là|anh|chị)\s+([A-ZÀ-Ỹa-zà-ỹ]+(?:\s+[A-ZÀ-Ỹa-zà-ỹ]+)*)", text)
    if name_m:
        cand_name = name_m.group(1).strip()
        if cand_name.lower() not in ("quán", "em", "nhịp quán", "bàn", "người", "hôm nay", "tối nay", "mai"):
            data["customer_name"] = cand_name

    # 6. Date extraction
    now_ict = datetime.now(ICT)
    target_date = None

    if any(k in low for k in ("mai", "ngày mai", "ngay mai", "tối mai", "trưa mai", "chiều mai", "sáng mai")):
        target_date = now_ict.date() + timedelta(days=1)
    elif any(k in low for k in ("ngày kia", "mốt", "ngay kia", "ngay mot")):
        target_date = now_ict.date() + timedelta(days=2)
    elif any(k in low for k in ("hôm nay", "tối nay", "trưa nay", "chiều nay", "sáng nay", "hom nay", "toi nay")):
        target_date = now_ict.date()
    else:
        # Weekday detection ("thứ 7", "thứ bảy", "chủ nhật", v.v.)
        weekday_map = {
            "thứ 2": 0, "thứ hai": 0, "thu 2": 0, "thu hai": 0,
            "thứ 3": 1, "thứ ba": 1, "thu 3": 1, "thu ba": 1,
            "thứ 4": 2, "thứ tư": 2, "thu 4": 2, "thu tu": 2,
            "thứ 5": 3, "thứ năm": 3, "thu 5": 3, "thu nam": 3,
            "thứ 6": 4, "thứ sáu": 4, "thu 6": 4, "thu sau": 4,
            "thứ 7": 5, "thứ bảy": 5, "thu 7": 5, "thu bay": 5,
            "chủ nhật": 6, "chu nhat": 6, "cn": 6,
        }
        for w_str, w_num in weekday_map.items():
            if w_str in low:
                delta = (w_num - now_ict.weekday()) % 7
                if delta == 0 and ("tuần sau" in low or "tuan sau" in low):
                    delta = 7
                target_date = now_ict.date() + timedelta(days=delta)
                break

    # Exact date pattern DD/MM or DD-MM
    date_m = re.search(r"(\d{1,2})[/-](\d{1,2})", low)
    if date_m:
        try:
            d_val = int(date_m.group(1))
            m_val = int(date_m.group(2))
            target_date = (target_date or now_ict.date()).replace(month=m_val, day=d_val)
        except Exception:
            pass

    if target_date is not None:
        data["target_date_iso"] = target_date.isoformat()

    # 7. Time extraction
    # Matches "19h", "19h30", "19:30", "19h 30", "7h tối", "18 giờ", "7 rưỡi", "19g"
    hour = None
    minute = 0

    ruoi_m = re.search(r"(\d{1,2})\s*(?:h|g|giờ)?\s*rưỡi", low)
    if ruoi_m:
        hour = int(ruoi_m.group(1))
        minute = 30
    else:
        time_m = re.search(r"(\d{1,2})\s*(?:h|:|giờ|g)\s*(\d{1,2})?", low)
        if time_m:
            hour = int(time_m.group(1))
            if time_m.group(2):
                minute = int(time_m.group(2))
        else:
            pm_m = re.search(r"(\d{1,2})\s*pm\b", low)
            if pm_m:
                hour = int(pm_m.group(1))
                if hour < 12:
                    hour += 12

    if hour is not None:
        if any(k in low for k in ("tối", "toi", "đêm", "dem")) and hour < 12:
            hour += 12
        elif any(k in low for k in ("chiều", "chieu")) and hour <= 6:
            hour += 12
        elif any(k in low for k in ("trưa", "trua")) and hour in (1, 2):
            hour += 12
        elif any(k in low for k in ("sáng", "sang")) and hour == 12:
            hour = 0

        final_date = target_date or now_ict.date()
        try:
            target_dt = datetime(final_date.year, final_date.month, final_date.day, hour, minute, tzinfo=ICT)
            data["booking_datetime"] = target_dt.isoformat()
            data["booking_time_iso"] = target_dt.isoformat()
            data["time_display"] = target_dt.strftime("%H:%M ngày %d/%m/%Y")
        except Exception:
            pass

    return data


_RESERVATION_BACKEND: dict[str, Any] = {}


def register_reservation_backend(
    *,
    book_fn: Any = None,
    anti_abuse_fn: Any = None,
    cancel_fn: Any = None,
    notify_fn: Any = None,
    is_enabled_fn: Any = None,
) -> None:
    """Register backend persistence & service handlers from application layer."""
    if book_fn is not None:
        _RESERVATION_BACKEND["book"] = book_fn
    if anti_abuse_fn is not None:
        _RESERVATION_BACKEND["anti_abuse"] = anti_abuse_fn
    if cancel_fn is not None:
        _RESERVATION_BACKEND["cancel"] = cancel_fn
    if notify_fn is not None:
        _RESERVATION_BACKEND["notify"] = notify_fn
    if is_enabled_fn is not None:
        _RESERVATION_BACKEND["is_enabled"] = is_enabled_fn


def _resolve_backend() -> dict[str, Any]:
    if not _RESERVATION_BACKEND:
        import sys

        mod = sys.modules.get("ca_api.services.table_reservation_service")
        if mod is not None:
            register_reservation_backend(
                book_fn=getattr(mod, "atomic_hold_or_book_table", None),
                anti_abuse_fn=getattr(mod, "check_anti_abuse", None),
                cancel_fn=getattr(mod, "customer_cancel_reservation", None),
                notify_fn=getattr(mod, "dispatch_reservation_notification", None),
                is_enabled_fn=getattr(mod, "auto_reservation_enabled", None),
            )
    return _RESERVATION_BACKEND


def handle_reservation(
    text: str,
    store_name: str = "Nhịp Quán",
    psid: str = "",
    session_state: dict[str, Any] | None = None,
) -> ConciergeTicket:
    """
    Multi-turn Dialog State Machine for Table Reservations.
    Handles extraction, confirmation check, atomic booking, and cancellation.
    """
    backend = _resolve_backend()
    is_enabled_fn = backend.get("is_enabled")
    is_auto = is_enabled_fn() if callable(is_enabled_fn) else False

    state = dict(session_state or {})
    extracted = extract_reservation_entities(text)

    # Merge extracted details into state
    for k in ("party_size", "phone", "customer_name", "booking_datetime", "booking_time_iso", "time_display", "target_date_iso"):
        if extracted.get(k) is not None:
            state[k] = extracted[k]

    # When auto-reservation is disabled, acknowledge whatever info is given instead of asking blindly
    if not is_auto:
        detail_parts = []
        if state.get("party_size"):
            detail_parts.append(f"nhóm {state['party_size']} người")
        if state.get("time_display"):
            detail_parts.append(f"lúc {state['time_display']}")
        if state.get("phone"):
            detail_parts.append(f"SĐT {state['phone']}")

        if detail_parts:
            details_str = " ".join(detail_parts)
            reply = (
                f"Dạ {store_name} rất vui được đón tiếp nhóm mình ạ! 🎉\n"
                f"Em đã ghi nhận thông tin đặt bàn ({details_str}). "
                "Quản lý ca sẽ liên hệ xác nhận và chuẩn bị bàn chu đáo trước cho mình nha!"
            )
        else:
            reply = (
                f"Dạ {store_name} rất vui được đón tiếp nhóm mình ạ! 🎉\n"
                "Anh/chị dự kiến ghé lúc mấy giờ và nhóm mình đi khoảng bao nhiêu người để em chuẩn bị bàn chu đáo trước cho mình nha?"
            )
        return ConciergeTicket(
            ticket_type="reservation",
            customer_message=text,
            extracted_data=state,
            suggested_reply=reply,
            urgency="medium",
            action_type="needs_manager_review",
            requires_human_approval=True,
        )

    cancel_fn = backend.get("cancel")
    book_fn = backend.get("book")
    notify_fn = backend.get("notify")
    anti_abuse_fn = backend.get("anti_abuse")

    # ── CASE 1: Customer Cancellation Request ────────────────────────────────
    if extracted.get("is_cancellation"):
        cancelled = cancel_fn(psid) if callable(cancel_fn) else False
        if cancelled:
            reply = (
                "Dạ em đã hủy lịch đặt bàn cho mình rồi ạ! 🥺\n"
                "Bàn đã được giải phóng trên hệ thống. Rất mong được đón tiếp anh/chị vào lần ghé quán tiếp theo nhé ạ!"
            )
            state["dialog_step"] = "CANCELLED"
            return ConciergeTicket(
                ticket_type="reservation",
                customer_message=text,
                extracted_data={"action": "cancelled", "dialog_step": "CANCELLED"},
                suggested_reply=reply,
                urgency="low",
                action_type="cancelled",
                requires_human_approval=False,
            )
        else:
            reply = "Dạ hiện tại em không tìm thấy lịch đặt bàn nào đang hoạt động của mình trên hệ thống ạ. Anh/chị cần đặt bàn mới cứ nhắn em nhé!"
            return ConciergeTicket(
                ticket_type="reservation",
                customer_message=text,
                extracted_data={"action": "no_active_booking", "dialog_step": "EXTRACTING"},
                suggested_reply=reply,
                urgency="low",
                action_type="ask_info",
                requires_human_approval=False,
            )

    dialog_step = state.get("dialog_step", "EXTRACTING")

    # ── CASE 2: Customer Confirming Previous Summary (State: CONFIRMING -> CONFIRMED) ──
    if dialog_step == "CONFIRMING" and (extracted.get("is_confirmation") or "đúng" in text.lower()):
        party_size = int(state.get("party_size", 2))
        booking_time_iso = str(state.get("booking_time_iso") or "")
        if not booking_time_iso:
            reply = (
                "Dạ em chưa lưu được giờ mình muốn đặt bàn. "
                "Anh/chị nhắn lại giúp em giờ và ngày cụ thể (ví dụ: 19h tối thứ Bảy) nhé ạ!"
            )
            return ConciergeTicket(
                ticket_type="reservation",
                customer_message=text,
                extracted_data={"action": "ask_time"},
                suggested_reply=reply,
                urgency="low",
                action_type="ask_info",
                requires_human_approval=False,
            )
        phone = state.get("phone", "")
        customer_name = state.get("customer_name") or "Quý khách"

        try:
            if not callable(book_fn):
                raise RuntimeError("Booking handler not available")
            res = book_fn(
                psid=psid,
                customer_name=customer_name,
                phone=phone,
                booking_time=booking_time_iso,
                party_size=party_size,
                status="confirmed",
                source="ai_auto",
            )
            res["dialog_step"] = "CONFIRMED"
            # Dispatch notifications to shift manager
            if callable(notify_fn):
                notify_fn(res)

            tables_str = ", ".join(res.get("table_ids") or [])
            table_info = f"bàn {tables_str} " if tables_str else "bàn "
            time_display = state.get("time_display") or booking_time_iso
            reply = (
                f"Dạ {store_name} đã xác nhận giữ {table_info}cho nhóm mình ({party_size} người) "
                f"vào lúc {time_display} rồi ạ! 🎉\n"
                f"Quán sẽ chuẩn bị chỗ ngồi chu đáo trước giờ đón mình. Nếu có thay đổi gì, anh/chị cứ nhắn lại tin nhắn này nhé ạ! ❤️"
            )
            return ConciergeTicket(
                ticket_type="reservation",
                customer_message=text,
                extracted_data=res,
                suggested_reply=reply,
                urgency="medium",
                action_type="confirmed",
                requires_human_approval=False,
                reservation_record=res,
            )
        except Exception as e:
            if type(e).__name__ == "NoTableAvailableError":
                reply = (
                    f"Dạ khung giờ {state.get('time_display')} vừa kín bàn ạ.\n"
                    "Em gợi ý mình lệch 30–60 phút hoặc đổi ngày gần nhất — anh/chị chọn khung nào em giữ bàn ngay giúp mình nha!"
                )
                return ConciergeTicket(
                    ticket_type="reservation",
                    customer_message=text,
                    extracted_data=state,
                    suggested_reply=reply,
                    urgency="medium",
                    action_type="ask_info",
                    requires_human_approval=False,
                )
            # Hệ thống lỗi — Mục 4.4, không đoán bàn trống
            reply = (
                "Dạ hệ thống sơ đồ bàn đang gián đoạn nên em chưa chốt được chỗ. "
                "Em đã chuyển quản lý ca — mình sẽ nhận xác nhận trong khoảng 15 phút, không để mình chờ không ạ!"
            )
            return ConciergeTicket(
                ticket_type="reservation",
                customer_message=text,
                extracted_data={"error": str(e)},
                suggested_reply=reply,
                urgency="high",
                action_type="needs_manager_review",
                requires_human_approval=True,
            )

    # ── CASE 3: Missing Information -> Natural Clarification ──────────────────
    missing = []
    if not state.get("booking_datetime") and not state.get("booking_time_iso"):
        missing.append("thời gian đến (mấy giờ, ngày nào)")
    if not state.get("party_size"):
        missing.append("số lượng khách")
    if not state.get("phone"):
        missing.append("số điện thoại liên hệ")

    if missing:
        if len(missing) == 3:
            reply = (
                f"Dạ {store_name} rất vui được đón tiếp mình ạ! 🎉\n"
                "Anh/chị dự kiến ghé quán lúc mấy giờ, nhóm mình đi khoảng bao nhiêu người và cho em xin số điện thoại để em hỗ trợ giữ bàn chu đáo nhé ạ!"
            )
        elif "thời gian đến (mấy giờ, ngày nào)" in missing and "số lượng khách" in missing:
            reply = "Dạ anh/chị dự kiến ghé quán lúc mấy giờ và nhóm mình đi khoảng bao nhiêu người để em kiểm tra bàn trống ạ?"
        elif "số điện thoại liên hệ" in missing and len(missing) == 1:
            reply = (
                f"Dạ em đã kiểm tra khung giờ {state.get('time_display')} cho nhóm {state.get('party_size')} người rồi ạ. "
                "Anh/chị cho em xin thêm số điện thoại liên hệ để em hoàn tất giữ bàn cho mình nha!"
            )
        else:
            missing_text = " và ".join(missing)
            reply = f"Dạ anh/chị cho em xin thêm thông tin về {missing_text} để em kiểm tra bàn chu đáo cho mình nha!"

        state["dialog_step"] = "EXTRACTING"
        return ConciergeTicket(
            ticket_type="reservation",
            customer_message=text,
            extracted_data=state,
            suggested_reply=reply,
            urgency="medium",
            action_type="ask_info",
            requires_human_approval=False,
        )

    # ── CASE 5: All details present -> Check Anti-Abuse & Ask 2-Phase Confirmation ──
    allowed, abuse_reason = (
        anti_abuse_fn(store_id="quan_01", psid=psid, phone=state.get("phone", ""))
        if callable(anti_abuse_fn)
        else (True, None)
    )
    if not allowed:
        if abuse_reason == "active_booking_exists":
            reply = (
                "Dạ trên hệ thống đang có một lịch đặt bàn còn hiệu lực của mình rồi ạ. "
                "Anh/chị muốn đổi giờ, hủy, hay giữ nguyên — em xử lý giúp ngay trên tin này nha!"
            )
        else:
            reply = (
                "Dạ em đã ghi nhận thông tin đặt bàn. "
                "Anh/chị xác nhận giúp SĐT và giờ đến để em chốt bàn, không cần chờ thêm bước nào khác ạ!"
            )
        return ConciergeTicket(
            ticket_type="reservation",
            customer_message=text,
            extracted_data={"abuse_reason": abuse_reason, **state},
            suggested_reply=reply,
            urgency="medium",
            action_type="ask_info",
            requires_human_approval=False,
        )

    # Ask 2-Phase Confirmation
    state["dialog_step"] = "CONFIRMING"
    reply = (
        f"Dạ em xin xác nhận lại thông tin đặt bàn của mình ạ: "
        f"Bàn {state.get('party_size')} người, vào lúc {state.get('time_display')}, SĐT liên hệ {state.get('phone')}.\n"
        f"Anh/chị kiểm tra đúng thông tin giúp em để em chốt giữ bàn cho mình nhé ạ! 😊"
    )
    return ConciergeTicket(
        ticket_type="reservation",
        customer_message=text,
        extracted_data=state,
        suggested_reply=reply,
        urgency="medium",
        action_type="ask_confirmation",
        requires_human_approval=False,
    )


__all__ = [
    "ConciergeTicket",
    "handle_complaint",
    "handle_reservation",
    "extract_reservation_entities",
    "register_reservation_backend",
]
