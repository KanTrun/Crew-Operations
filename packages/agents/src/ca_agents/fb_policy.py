"""FB-POLICY: deterministic moderation policy engine for AG-FBPAGE (ADR-002 compliant).

Maps (intent, confidence, context) -> PolicyDecision. No LLM, no I/O, no clock
(expires_at is computed by the API layer, not here).

Thứ tự ưu tiên quyết định (kế hoạch §3.3 — KHÔNG tự đổi):
    1. Từ khóa escalate Chủ quán (an toàn) thắng mọi nhánh
    2. Khiếu nại → priority_review
    3. Ngoài phạm vi → block_polite
    4. Thiếu dữ kiện KB / giá vượt trần → queue
    5. Intent bắt buộc duyệt → queue
    6. Loop guard (hỏi lại ≥ 3 lần) → queue
    7. Confidence thấp (< 0.60) → queue
    8. Whitelist auto + đủ ngưỡng → auto_send (comment siết riêng)
"""

from __future__ import annotations

from dataclasses import dataclass

from ca_contracts import FbPolicyAction, PolicyDecision

from ca_agents.guardrails import normalize_text

# ── Ngưỡng & hằng số chính sách (gom một chỗ — quyết định kinh doanh, §3.2) ──

AUTO_THRESHOLD: dict[str, float] = {
    "chao_hoi": 0.90,
    "hoi_gio_dia_chi": 0.85,
    "hoi_menu_gia": 0.85,
}
AUTO_THRESHOLD_COMMENT = 0.95
COMMENT_SAFE_INTENTS = frozenset({"chao_hoi", "hoi_gio_dia_chi"})

LOW_CONFIDENCE_QUEUE = 0.60
REPEAT_ASK_LIMIT = 3

SLA_MINUTES_PRIORITY_REVIEW = 5
SLA_MINUTES_QUEUE_REVIEW = 10
SLA_MINUTES_COMMENT_QUEUE = 15
SLA_MINUTES_ESCALATE_OWNER = 15

# Intent bắt buộc con người duyệt — không bao giờ auto (§3.2)
INTENTS_REQUIRING_APPROVAL = frozenset(
    {"hoi_khuyen_mai", "tu_van_mon", "yeu_cau_dac_biet"}
)
INTENT_COMPLAINT = "khieu_nai_gop_y"
INTENT_OTHER = "khac"

# Từ khóa escalate Chủ quán — CHỈ 1 BẢN không dấu (normalize_text tự quy về
# dạng này; kế hoạch §6.2c). Danh sách là quyết định kinh doanh, không tự thêm.
OWNER_ESCALATION_KEYWORDS = (
    "ngo doc", "dau bung", "di ung", "thai san", "tre em", "con toi",
    "chau toi", "hoa don do", "hop dong", "hoan tien", "boi thuong",
    "chuyen khoan", "bao chi", "co quan chuc nang", "cong an", "so y te",
    "luat su", "gap chu", "gap quan ly",
)

# Từ khóa khiếu nại nặng — QL xử lý trong 5 phút, chưa tới mức Chủ quán
COMPLAINT_HEAVY_KEYWORDS = (
    "tay chay", "1 sao", "review xau", "boc phot", "that vong",
)

# Ngoài phạm vi — trả template lịch sự duy nhất, không escalate
OUT_OF_SCOPE_KEYWORDS = (
    "chinh tri", "ton giao", "dang", "doi thu",
)


@dataclass(frozen=True)
class PolicyContext:
    """Ngữ cảnh đưa vào decide() — tầng gọi chịu trách nhiệm tính các flag.

    price_above_limit: tầng gọi đọc config (auto_price_cap_vnd) rồi set flag —
    policy không hard-code số tiền trong logic.
    """

    source: str                     # "messenger" | "comment"
    sensitive_post: bool = False    # comment trên bài nhạy cảm (giá/tin buồn/lùm xùm)
    repeat_ask_count: int = 0       # cùng câu hỏi chưa được trả lời trong thread
    kb_has_fact: bool = True        # dữ kiện yêu cầu có trong chatbot_kb/menu_mon?
    price_above_limit: bool = False # món được hỏi có giá vượt trần config?
    recent_messages: tuple[str, ...] = ()  # 2-3 tin gần nhất cùng thread (~5 phút)
    reservation_auto_eligible: bool = False # Bàn trống & hợp lệ theo logic auto-reservation


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(k in text for k in keywords)


def _escalation_text(message_text: str, ctx: PolicyContext) -> str:
    """Ghép tin hiện tại với ngữ cảnh gần nhất — chỉ dùng cho nhóm an toàn/escalate
    (kế hoạch §6.2d: không áp cho toàn bộ intent để tránh làm loãng ngữ nghĩa)."""
    if not ctx.recent_messages:
        return message_text
    return " ".join((*ctx.recent_messages, message_text))


def _queue(
    reason: str,
    intent: str,
    confidence: float,
    role: str = "quan_ly",
    sla: int = SLA_MINUTES_QUEUE_REVIEW,
    flagged: tuple[str, ...] = (),
) -> PolicyDecision:
    return PolicyDecision(
        action=FbPolicyAction.QUEUE_REVIEW,
        reason=reason,
        intent=intent,
        confidence=confidence,
        assigned_role=role,
        sla_minutes=sla,
        flagged_reasons=list(flagged),
    )


def decide(
    intent: str,
    confidence: float,
    message_text: str,
    ctx: PolicyContext,
) -> PolicyDecision:
    """Deterministic decision. Order matters: safety keywords > scope > queue > auto."""
    low = normalize_text(message_text)

    # 1. An toàn trước: keyword escalate thắng mọi thứ (kể cả heavy-complaint)
    escalation_text = normalize_text(_escalation_text(message_text, ctx))
    if _has_any(escalation_text, OWNER_ESCALATION_KEYWORDS):
        flagged: tuple[str, ...] = ()
        # Keyword khớp nhưng classifier không đồng thuận → ghi tín hiệu giám sát
        # chất lượng bộ từ khóa (kế hoạch §6.2c) — quyết định vẫn tất định.
        if intent not in (INTENT_COMPLAINT, "yeu_cau_dac_biet"):
            flagged = ("keyword_matched_ambiguous",)
        return PolicyDecision(
            action=FbPolicyAction.ESCALATE_OWNER,
            reason="owner_escalation_keyword",
            intent=intent,
            confidence=confidence,
            assigned_role="chu_quan",
            sla_minutes=SLA_MINUTES_ESCALATE_OWNER,
            flagged_reasons=list(flagged),
        )

    # 2. Khiếu nại → priority_review (nhẹ hay nặng đều con người, SLA 5 phút)
    if intent == INTENT_COMPLAINT:
        return PolicyDecision(
            action=FbPolicyAction.PRIORITY_REVIEW,
            reason=(
                "heavy_complaint"
                if _has_any(low, COMPLAINT_HEAVY_KEYWORDS)
                else "complaint_requires_human"
            ),
            intent=intent,
            confidence=confidence,
            assigned_role="quan_ly",
            sla_minutes=SLA_MINUTES_PRIORITY_REVIEW,
        )

    # 3. Ngoài phạm vi — chặn lịch sự, không báo chủ
    if intent == INTENT_OTHER and _has_any(low, OUT_OF_SCOPE_KEYWORDS):
        return PolicyDecision(
            action=FbPolicyAction.BLOCK_POLITE,
            reason="out_of_scope",
            intent=intent,
            confidence=confidence,
        )

    # 4. Không có dữ kiện trong KB / giá vượt trần → không bịa, queue
    if intent in ("hoi_gio_dia_chi", "hoi_menu_gia") and (
        not ctx.kb_has_fact or ctx.price_above_limit
    ):
        return _queue("fact_not_in_kb_or_price_limit", intent, confidence)

    # 5. Intent đặt bàn hoặc intent bắt buộc duyệt
    if intent == "dat_ban":
        if not ctx.reservation_auto_eligible:
            return _queue("intent_requires_approval", intent, confidence)
        if confidence >= 0.85:
            return PolicyDecision(
                action=FbPolicyAction.AUTO_SEND,
                reason="reservation_auto_confirmed",
                intent=intent,
                confidence=confidence,
            )
        return _queue("low_confidence", intent, confidence)
    elif intent in INTENTS_REQUIRING_APPROVAL:
        return _queue("intent_requires_approval", intent, confidence)

    # 6. Loop guard: hỏi lại lần 3 → queue
    if ctx.repeat_ask_count >= REPEAT_ASK_LIMIT:
        return _queue("repeat_ask_loop", intent, confidence)

    # 7. Confidence thấp → queue
    if confidence < LOW_CONFIDENCE_QUEUE:
        return _queue("low_confidence", intent, confidence)

    # 8. AUTO — chỉ khi intent whitelist + đủ conf + nguồn an toàn
    threshold = AUTO_THRESHOLD.get(intent)
    if threshold is None:
        return _queue("intent_not_whitelisted_for_auto", intent, confidence)
    if ctx.source == "comment" and (
        intent not in COMMENT_SAFE_INTENTS
        or confidence < AUTO_THRESHOLD_COMMENT
        or ctx.sensitive_post
    ):
        return _queue(
            "comment_policy", intent, confidence, sla=SLA_MINUTES_COMMENT_QUEUE
        )
    if confidence >= threshold:
        return PolicyDecision(
            action=FbPolicyAction.AUTO_SEND,
            reason="whitelisted_intent_confident",
            intent=intent,
            confidence=confidence,
        )
    return _queue("below_auto_threshold", intent, confidence)
