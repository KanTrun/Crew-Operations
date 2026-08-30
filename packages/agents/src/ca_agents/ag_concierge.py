"""
AG-CONCIERGE: Special Case & Complaint Resolution Agent for Nhịp Quán.

Specialized in:
- Crisis de-escalation & Complaint handling via HEAR Framework (Hear, Empathize, Apologize, Resolve).
- Table booking & large group event requests (gathering time, party size, seating preference).
- Packaging sensitive cases for managerial review and direct customer outreach.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConciergeTicket:
    ticket_type: str             # "complaint" | "reservation" | "special_request"
    customer_message: str        # Raw message from customer
    extracted_data: dict[str, Any]  # Extracted metadata (party size, time, phone, issue)
    suggested_reply: str         # Polite holding reply to customer
    urgency: str                 # "high" | "medium" | "low"


def handle_complaint(
    text: str,
    customer_name: str | None = None
) -> ConciergeTicket:
    """
    Handle customer dissatisfaction and complaints with sincere empathy.
    Applies HEAR framework to de-escalate and collect contact info for management.
    """
    name = customer_name or "mình"
    reply = (
        f"Dạ em thật sự xin lỗi {name} vì trải nghiệm chưa được trọn vẹn hôm nay ạ! 🥺\n"
        "Nhịp Quán rất trân trọng mọi góp ý của khách hàng và em đã chuyển phản ánh này ngay cho Quản lý quán để kiểm điểm quy trình phục vụ.\n"
        "Anh/chị cho em xin số điện thoại để Quản lý liên hệ hỗ trợ và gửi lời xin lỗi trực tiếp đến mình được không ạ?"
    )
    return ConciergeTicket(
        ticket_type="complaint",
        customer_message=text,
        extracted_data={"issue_summary": text[:160]},
        suggested_reply=reply,
        urgency="high",
    )


def handle_reservation(
    text: str,
    store_name: str = "Nhịp Quán"
) -> ConciergeTicket:
    """
    Handle table booking and reservation inquiries.
    """
    reply = (
        f"Dạ {store_name} rất vui được đón tiếp nhóm mình ạ! 🎉\n"
        "Anh/chị dự kiến ghé quán lúc mấy giờ và nhóm mình đi khoảng bao nhiêu người để em chuẩn bị bàn chu đáo trước cho mình nha?"
    )
    return ConciergeTicket(
        ticket_type="reservation",
        customer_message=text,
        extracted_data={"request_summary": text[:160]},
        suggested_reply=reply,
        urgency="medium",
    )


__all__ = ["ConciergeTicket", "handle_complaint", "handle_reservation"]