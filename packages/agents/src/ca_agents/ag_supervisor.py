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

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone

    UTC = timezone.utc


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
    # Mở rộng theo kế hoạch chatbot moderation §3.6
    r"lương\s*(nhân\s*viên|nv)",
    r"(số|so)\s*điện\s*thoại\s*(nội\s*bộ|chủ\s*quán|quản\s*lý)",
    r"chi\s*phí\s*(nguyên\s*liệu|vốn|mặt\s*bằng)",
    r"(mật\s*khẩu|mat\s*khau)\s*(wifi)?\s*(quản\s*lý|admin|root)",
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


# HEAR bắt buộc cho draft khiếu nại (kế hoạch §3.6): xin lỗi → ghi nhận → hỏi SĐT
# → cam kết Quản lý gọi lại. Thiếu bước nào thì báo rõ để tầng API hạ xuống queue.
_HEAR_STEPS: tuple[tuple[str, str], ...] = (
    ("xin_loi", r"xin\s*lỗi|xin\s*loi"),
    ("so_dien_thoai", r"số\s*điện\s*thoại|sđt|so\s*dien\s*thoai"),
    ("quan_ly", r"quản\s*lý|quan\s*ly"),
)

_HEAR_REGEXES = tuple((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _HEAR_STEPS)


def check_hear_structure(response: str) -> tuple[bool, tuple[str, ...]]:
    """Return (ok, missing_steps). Used by API layer: complaint draft missing
    a HEAR step is downgraded to queue_review, never auto-sent."""
    missing = tuple(name for name, rx in _HEAR_REGEXES if not rx.search(response or ""))
    return (len(missing) == 0, missing)


def audit_conversations_summary(threads: list[dict[str, Any]]) -> dict[str, Any]:
    """Post-flight audit: Analyze conversation logs to compute quality metrics for management."""
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


def run_nightly_cskh_reflection(
    threads: list[dict[str, Any]],
    store_id: str = "quan_01",
) -> dict[str, Any]:
    """Tự phê bình & đánh giá chất lượng CSKH hàng đêm (Nightly Reflection Agent).

    Phân tích toàn bộ hội thoại trong ngày:
    1. Chấm điểm CSAT dự đoán (1-10) và tỷ lệ tuân thủ quy chuẩn H.E.A.R.
    2. Phát hiện lỗ hổng tri thức (Unresolved Inquiries / Knowledge Gaps).
    3. Tự động sinh Đề xuất Cẩm nang (Playbook Rule Proposals) để gửi chủ quán duyệt.
    """
    total = len(threads)
    if total == 0:
        return {
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "store_id": store_id,
            "total_conversations": 0,
            "csat_score": 10.0,
            "hear_compliance_rate": 100.0,
            "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0},
            "unresolved_inquiries": [],
            "learning_recommendations": ["Hôm nay không phát sinh hội thoại khách hàng nào cần rút kinh nghiệm."],
            "playbook_rule_proposals": [],
            "summary_text": "Hôm nay không có hội thoại phát sinh.",
        }

    positive_count = 0
    neutral_count = 0
    negative_count = 0
    complaints = 0
    hear_passed = 0

    # Danh mục các lỗ hổng tri thức thường gặp để gom cụm
    topic_patterns = [
        ("bai_do_xe", r"đậu\s*xe|đỗ\s*xe|bãi\s*xe|ô\s*tô|xe\s*hơi", "Chỗ đậu xe ô tô & bãi giữ xe"),
        ("ban_hat_cafe", r"mua\s*hạt|bán\s*hạt|hạt\s*cà\s*phê|pha\s*phin", "Bán hạt cà phê đóng gói mang về"),
        ("to_chuc_su_kien", r"sinh\s*nhật|sự\s*kiện|thuê\s*quán|bao\s*quán|họp\s*nhóm", "Chính sách thuê không gian & tổ chức sự kiện"),
        ("xuat_hoa_don", r"hóa\s*đơn\s*đỏ|vat|hóa\s*đơn\s*công\s*ty", "Xuất hóa đơn VAT cho doanh nghiệp"),
        ("thu_cung_pet", r"thú\s*cưng|chó|mèo|pet", "Chính sách tiếp đón thú cưng (Pet-friendly)"),
    ]
    unresolved_map: dict[str, dict[str, Any]] = {}

    for th in threads:
        # Lấy nội dung tin nhắn của khách
        msgs = th.get("messages") or []
        cust_texts = [m.get("text", "") for m in msgs if m.get("from_customer")]
        combined_cust = " ".join(cust_texts).lower()

        # Lấy câu phản hồi của bot/quán
        replies = th.get("replies") or []
        last_reply = replies[-1].get("text", "") if replies else str(th.get("suggested_reply") or "")

        # 1. Phân loại cảm xúc & CSAT
        is_complaint = th.get("intent") == "khieu_nai_gop_y" or any(
            k in combined_cust for k in ("thất vọng", "dở", "tệ", "chậm", "thái độ", "đau bụng", "bực")
        )

        if is_complaint:
            complaints += 1
            negative_count += 1
            # Đánh giá chuẩn HEAR
            ok_hear, _ = check_hear_structure(last_reply)
            if ok_hear:
                hear_passed += 1
        elif any(k in combined_cust for k in ("cảm ơn", "cam on", "tuyệt", "ngon", "ok", "dạ vâng")):
            positive_count += 1
        else:
            neutral_count += 1

        # 2. Quét lỗ hổng tri thức (chưa biết thông tin / trả lời chung chung)
        is_fallback_reply = any(
            k in last_reply.lower() for k in ("chưa có thông tin", "hỏi lại quản lý", "đợi em một xíu", "kiểm tra lại")
        )
        for slug, pattern, title in topic_patterns:
            if re.search(pattern, combined_cust, re.IGNORECASE):
                if is_fallback_reply or th.get("pending_approval"):
                    entry = unresolved_map.setdefault(slug, {
                        "slug": slug,
                        "title": title,
                        "count": 0,
                        "sample_questions": [],
                    })
                    entry["count"] += 1
                    if len(entry["sample_questions"]) < 3 and cust_texts:
                        entry["sample_questions"].append(cust_texts[0])

    # 3. Tính điểm CSAT & Tỷ lệ HEAR
    hear_rate = (hear_passed / complaints * 100.0) if complaints > 0 else 100.0
    # Công thức CSAT dự đoán: (Positive * 10 + Neutral * 8 + Negative * (4 nếu đủ HEAR, 2 nếu thiếu HEAR)) / Total
    total_score = (
        positive_count * 10.0
        + neutral_count * 8.0
        + (hear_passed * 5.0 + (complaints - hear_passed) * 2.0)
    )
    csat_score = round(min(10.0, max(1.0, total_score / total)), 1)

    # 4. Tạo các đề xuất Cẩm nang quán (Playbook Rule Proposals)
    proposals = []
    recommendations = []

    if complaints > 0 and hear_rate < 100.0:
        recommendations.append(
            f"Phát hiện {complaints - hear_passed} ca khiếu nại chưa áp dụng đủ 3 bước H.E.A.R (Xin lỗi - Lấy SĐT - Quản lý gọi lại). Cần kiểm soát chặt câu từ trước khi gửi."
        )
    elif complaints > 0 and hear_rate == 100.0:
        recommendations.append(
            f"Tất cả {complaints} ca khiếu nại trong ngày đều được xử lý chuẩn mực theo quy trình H.E.A.R."
        )

    for slug, item in unresolved_map.items():
        count = item["count"]
        title = item["title"]
        recommendations.append(
            f"Có {count} khách hỏi về \"{title}\" nhưng quán chưa có câu trả lời tự động chuẩn xác."
        )
        proposals.append({
            "proposal_id": f"prop_{slug}_{datetime.now(UTC).strftime('%Y%m%d')}",
            "title": f"Bổ sung quy định: {title}",
            "topic": title,
            "frequency": count,
            "sample_questions": item["sample_questions"],
            "suggested_rule": f"Khi khách hỏi về {title.lower()}, giải thích rõ chính sách của quán và hỗ trợ chu đáo.",
            "status": "cho_chu_duyet",
        })

    if not recommendations:
        recommendations.append("Đội ngũ CSKH và bot hôm nay hoạt động xuất sắc, không ghi nhận bất thường.")

    summary_text = (
        f"Đánh giá CSAT: {csat_score}/10.0 | Tỷ lệ tuân thủ HEAR: {hear_rate:.0f}%. "
        f"Ghi nhận {len(proposals)} chủ đề khách quan tâm cần cập nhật vào Cẩm nang quán."
    )

    return {
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "store_id": store_id,
        "total_conversations": total,
        "csat_score": csat_score,
        "hear_compliance_rate": round(hear_rate, 1),
        "sentiment_breakdown": {
            "positive": positive_count,
            "neutral": neutral_count,
            "negative": negative_count,
        },
        "unresolved_inquiries": list(unresolved_map.values()),
        "learning_recommendations": recommendations,
        "playbook_rule_proposals": proposals,
        "summary_text": summary_text,
    }


__all__ = [
    "SupervisionResult",
    "supervise_outgoing_response",
    "check_hear_structure",
    "audit_conversations_summary",
    "run_nightly_cskh_reflection",
]

