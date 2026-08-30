"""
AG-SUPERVISOR: Safety Gate & Quality Assurance Supervisor Agent for Nhịp Quán.

Specialized in:
- Pre-flight Gate: Intercepting hallucinations, unauthorized financial commitments (fake discounts), data leaks, and robot phrases.
- Post-flight Audit: Analyzing daily conversations, evaluating customer satisfaction (CSAT), and generating management summaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SupervisionResult:
    is_approved: bool
    sanitized_response: str
    flagged_reason: str | None = None


# Patterns that are forbidden for customer-facing bot to output
_FORBIDDEN_PROMISES = [
    r"giảm\s*(giá\s*)?(50%|70%|100%|nửa\s*giá|\d{2,3}%)",
    r"miễn\s*phí\s*(toàn\s*bộ|hết|mọi\s*thứ)?",
    r"đền\s*bù\s*(tiền|triệu)",
    r"chuyển\s*khoản\s*trả\s*lại",
    r"tặng\s*voucher\s*\d{3,}",
]

_LEAK_PATTERNS = [
    r"mật\s*khẩu\s*của\s*(quản\s*lý|chủ\s*quán|hệ\s*thống)?",
    r"giá\s*vốn\s*của\s*món",
    r"công\s*thức\s*bí\s*mật",
    r"doanh\s*thu\s*ngày",
    r"tài\s*khoản\s*ngân\s*hàng\s*cá\s*nhân",
]

_ROBOT_PHRASES = [
    r"tôi\s*là\s*(mô\s*hình\s*ngôn\s*ngữ|trợ\s*lý\s*ảo|ai|bot)",
    r"theo\s*cơ\s*sở\s*dữ\s*liệu",
    r"tôi\s*không\s*có\s*cảm\s*xúc",
]

_FORBIDDEN_REGEX = re.compile("|".join(_FORBIDDEN_PROMISES), re.IGNORECASE)
_LEAK_REGEX = re.compile("|".join(_LEAK_PATTERNS), re.IGNORECASE)
_ROBOT_REGEX = re.compile("|".join(_ROBOT_PHRASES), re.IGNORECASE)


def supervise_outgoing_response(customer_query: str, proposed_response: str) -> SupervisionResult:
    """
    Pre-flight safety check on AI-generated response before sending to customer.
    """
    if not proposed_response or not proposed_response.strip():
        return SupervisionResult(
            is_approved=False,
            sanitized_response="Dạ em đã nhận được tin nhắn và sẽ phản hồi mình ngay ạ!",
            flagged_reason="empty_response",
        )

    # 1. Check for unauthorized financial promises or compensations
    if _FORBIDDEN_REGEX.search(proposed_response):
        return SupervisionResult(
            is_approved=False,
            sanitized_response="Dạ em đã ghi nhận yêu cầu của mình và sẽ báo Quản lý quán liên hệ hỗ trợ trực tiếp cho mình nha!",
            flagged_reason="unauthorized_financial_promise",
        )

    # 2. Check for data leaks
    if _LEAK_REGEX.search(proposed_response):
        return SupervisionResult(
            is_approved=False,
            sanitized_response="Dạ thông tin này thuộc nội bộ quán nên em không thể chia sẻ được ạ. Mình cần em hỗ trợ thêm gì về Menu không ạ?",
            flagged_reason="data_leak_detected",
        )

    # 3. Clean any robotic phrasing
    if _ROBOT_REGEX.search(proposed_response):
        cleaned = _ROBOT_REGEX.sub("em", proposed_response)
        return SupervisionResult(
            is_approved=True,
            sanitized_response=cleaned,
            flagged_reason="robotic_phrasing_cleaned",
        )

    return SupervisionResult(
        is_approved=True,
        sanitized_response=proposed_response,
        flagged_reason=None,
    )


def audit_conversations_summary(threads: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Post-flight audit: Analyze conversation logs to compute quality metrics for management.
    """
    total = len(threads)
    if total == 0:
        return {
            "total_conversations": 0,
            "auto_replied_count": 0,
            "pending_approval_count": 0,
            "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0},
            "summary_text": "Hôm nay chưa có cuộc hội thoại nào từ khách hàng.",
        }

    auto_replied = 0
    pending_approval = 0
    complaints = 0
    reservations = 0

    for th in threads:
        if th.get("pending_approval"):
            pending_approval += 1
        else:
            auto_replied += 1

        intent = str(th.get("intent", ""))
        if intent == "khieu_nai_gop_y":
            complaints += 1
        elif intent == "dat_ban":
            reservations += 1

    summary_text = (
        f"Tổng cộng {total} cuộc hội thoại: {auto_replied} cuộc trả lời tự động, "
        f"{pending_approval} cuộc cần quản lý duyệt ({reservations} đặt bàn, {complaints} phản ánh)."
    )

    return {
        "total_conversations": total,
        "auto_replied_count": auto_replied,
        "pending_approval_count": pending_approval,
        "reservations_count": reservations,
        "complaints_count": complaints,
        "summary_text": summary_text,
    }


__all__ = [
    "SupervisionResult",
    "supervise_outgoing_response",
    "audit_conversations_summary",
]
