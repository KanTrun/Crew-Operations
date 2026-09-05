"""FB moderation service — cầu nối webhook ↔ policy engine ↔ review queue.

Tầng API duy nhất được ghi DB (agent không ghi DB — ADR-002). Mọi tin nhắn
Messenger inbound đi qua đây trước khi được trả lời tự động hay đẩy queue.

Luồng (kế hoạch §3.3 + bản vá §6.2):
    L0 idempotency/echo  — ở webhook handler (channels.py)
    L1 input guardrail   (ca_agents.guardrails)
    L2 rate limit        (ca_agents.fb_rate_limiter) + blacklist DB
    L3 intent classify   (ag_fbpage.detect_customer_psychology — deterministic)
    L4 policy decide     (ca_agents.fb_policy)  ← tất định, không LLM
    L5 supervisor        (ca_agents.ag_supervisor) — hạ auto → queue nếu flag
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from typing import Any

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from ca_agents.ag_fbpage import build_human_response, detect_customer_psychology
from ca_agents.ag_supervisor import supervise_outgoing_response
from ca_agents.fb_policy import PolicyContext, decide
from ca_agents.fb_rate_limiter import SlidingWindowRateLimiter
from ca_agents.guardrails import check_input_guardrail
from ca_contracts import FbPolicyAction, PolicyDecision

from ca_api.persist import (
    audit_add,
    fb_blacklist_bump,
    fb_blacklist_check,
    fb_escalation_add,
    fb_review_insert,
)

_RATE_LIMITER = SlidingWindowRateLimiter()


def fb_auto_send_enabled() -> bool:
    """Feature flag — kế hoạch §5.5. Mặc định OFF; Chủ quán bật qua env/API.

    Single source of truth cho cả service (ghi queue/stats) và webhook (gửi
    thật). Khi OFF, nhánh auto_send được ghi là 'pending' cho QL duyệt —
    không bao giờ ghi 'auto_sent' khi chưa gửi thật.
    """
    env = os.environ.get("NHIPQUAN_FB_AUTO_SEND", "0").strip().lower()
    return env in {"1", "true", "yes", "on"}


# Ngưỡng giá auto (kế hoạch §6.3.2 — chính sách kinh doanh, đọc env để Chủ quán
# chỉnh không cần sửa code; default 100_000 đúng số đã thống nhất).

def fb_auto_price_cap_vnd() -> int:
    return int(os.environ.get("NHIPQUAN_FB_AUTO_PRICE_CAP_VND", "100000"))


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sla_expiry(sla_minutes: int | None) -> str | None:
    if not sla_minutes:
        return None
    return (datetime.now(UTC) + timedelta(minutes=sla_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _event_time_iso(timestamp: float) -> str | None:
    if timestamp <= 0:
        return None
    seconds = timestamp / 1000 if timestamp > 1e11 else timestamp
    try:
        return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OSError, OverflowError, ValueError):
        return None


def queue_fb_non_text(*, psid: str, event_id: str, description: str) -> int:
    """Đưa attachment/postback vào hàng duyệt mà không suy đoán ý định."""
    review_id = fb_review_insert(
        {
            "source": "messenger",
            "external_thread_id": f"fb_{psid}",
            "external_psid": psid,
            "message_text": description,
            "detected_intent": "khac",
            "confidence": 1.0,
            "policy_action": FbPolicyAction.QUEUE_REVIEW.value,
            "assigned_role": "quan_ly",
            "proposed_response": None,
            "flagged_reasons": ["non_text_event"],
            "trace_id": event_id or uuid.uuid4().hex[:12],
            "created_at": _now_iso(),
            "expires_at": _sla_expiry(10),
        }
    )
    audit_add(
        _now_iso(),
        "fb_policy_engine",
        FbPolicyAction.QUEUE_REVIEW.value,
        {"psid": psid, "reason": "non_text_event", "review_id": review_id},
    )
    return review_id


def _menu_price_above_cap(menu: list[dict[str, Any]], text: str) -> bool:
    low = text.lower()
    for m in menu:
        ten = str(m.get("ten") or "").lower()
        if ten and ten in low:
            try:
                return int(m.get("gia") or 0) > fb_auto_price_cap_vnd()
            except (TypeError, ValueError):
                return False
    return False


def _kb_has_fact(public_context: dict[str, Any] | None, text: str) -> bool:
    ctx = public_context or {}
    profile = ctx.get("profile") or {}
    menu = ctx.get("menu") or []
    low = text.lower()
    if any(k in low for k in ("mấy giờ", "may gio", "giờ mở", "gio mo", "đóng cửa", "dong cua")):
        return bool(str(profile.get("gio_mo_cua") or "").strip())
    if any(k in low for k in ("ở đâu", "o dau", "địa chỉ", "dia chi", "vị trí", "vi tri")):
        return bool(str(profile.get("dia_chi") or "").strip())
    if "wifi" in low:
        return bool(str(profile.get("wifi") or "").strip())
    if any(k in low for k in ("giá", "gia", "tiền", "tien", "menu", "bao nhiêu", "bao nhieu")):
        return bool(menu)
    return bool(menu) or bool(profile)


def moderate_fb_message(
    *,
    psid: str,
    text: str,
    message_id: str,
    timestamp: float,
    public_context: dict[str, Any] | None = None,
    repeat_ask_count: int = 0,
    source: str = "messenger",
    post_id: str | None = None,
    post_is_sensitive: bool = False,
    external_user_name: str | None = None,
) -> dict[str, Any]:
    """Xử lý 1 tin Messenger qua 5 lớp cổng; ghi queue khi cần con người.

    Trả về dict: action, review_id, response (chỉ khi auto_send), reason,
    flagged_reasons, intent, confidence.
    """
    # L1 — Input guardrail
    guard = check_input_guardrail(text)
    if not guard.is_safe:
        _audit_block(psid, text, "injection", guard.reason or "unsafe")
        return {
            "action": FbPolicyAction.BLOCK_SILENT.value,
            "review_id": None,
            "response": None,
            "reason": guard.reason,
            "flagged_reasons": [],
        }

    # L2 — blacklist DB + rate limit in-memory
    if fb_blacklist_check(psid):
        return {
            "action": FbPolicyAction.BLOCK_SILENT.value,
            "review_id": None,
            "response": None,
            "reason": "psid_blacklisted",
            "flagged_reasons": [],
        }
    verdict = _RATE_LIMITER.check(psid)
    if not verdict.allowed:
        if verdict.blacklisted:
            blocked_until = (datetime.now(UTC) + timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            fb_blacklist_bump(
                psid, strikes=3, blocked_until=blocked_until,
                reason=verdict.reason or "rate_limit",
            )
        _audit_block(psid, text, "rate_limit", verdict.reason or "")
        return {
            "action": FbPolicyAction.BLOCK_SILENT.value,
            "review_id": None,
            "response": None,
            "reason": verdict.reason,
            "flagged_reasons": [],
        }

    # L3 — Intent classify (deterministic)
    _, intent, confidence = detect_customer_psychology(guard.sanitized_text)

    # L4 — Policy decide (tất định)
    ctx = PolicyContext(
        source=source,
        sensitive_post=post_is_sensitive,
        repeat_ask_count=repeat_ask_count,
        kb_has_fact=_kb_has_fact(public_context, guard.sanitized_text),
        price_above_limit=_menu_price_above_cap(
            (public_context or {}).get("menu") or [], guard.sanitized_text
        ),
    )
    decision = decide(intent, confidence, guard.sanitized_text, ctx)
    flagged = list(decision.flagged_reasons)

    # L5 — Supervisor gate cho nhánh auto; hạ xuống queue nếu flag
    response: str | None = None
    if decision.action == FbPolicyAction.AUTO_SEND:
        reply, requires_approval, _agent = build_human_response(
            intent, "neutral", guard.sanitized_text, public_context
        )
        sup = supervise_outgoing_response(guard.sanitized_text, reply)
        if not sup.is_approved or requires_approval:
            decision = PolicyDecision(
                action=FbPolicyAction.QUEUE_REVIEW,
                reason="supervisor_downgrade",
                intent=intent,
                confidence=confidence,
                assigned_role="quan_ly",
                sla_minutes=10,
                flagged_reasons=flagged + [sup.flagged_reason or "supervisor"],
            )
            flagged = decision.flagged_reasons
        else:
            response = sup.sanitized_response

    # Ghi review queue cho mọi thứ cần con người nhìn
    review_id: int | None = None
    if decision.action in (
        FbPolicyAction.QUEUE_REVIEW,
        FbPolicyAction.PRIORITY_REVIEW,
        FbPolicyAction.ESCALATE_OWNER,
    ):
        review_id = fb_review_insert(
            {
                "source": source,
                "external_thread_id": message_id if source == "comment" else f"fb_{psid}",
                "external_psid": psid,
                "external_user_name": external_user_name,
                "post_id": post_id,
                "post_is_sensitive": post_is_sensitive,
                "message_text": guard.sanitized_text,
                "detected_intent": intent,
                "confidence": confidence,
                "policy_action": decision.action.value,
                "assigned_role": decision.assigned_role,
                "proposed_response": response or decision.reason,
                "flagged_reasons": flagged,
                "trace_id": uuid.uuid4().hex[:12],
                "created_at": _now_iso(),
                "event_at": _event_time_iso(timestamp),
                "expires_at": _sla_expiry(decision.sla_minutes),
            }
        )
        if decision.action == FbPolicyAction.ESCALATE_OWNER:
            fb_escalation_add(
                review_id,
                escalated_to="chu_quan",
                reason=decision.reason,
                notified_channel="in_app",
            )
    elif decision.action == FbPolicyAction.AUTO_SEND:
        if fb_auto_send_enabled() and source == "messenger":
            # Claim giao tin; webhook chỉ đánh dấu auto_sent sau khi Graph xác nhận.
            review_id = fb_review_insert(
                {
                    "source": source,
                    "external_thread_id": message_id if source == "comment" else f"fb_{psid}",
                    "external_psid": psid,
                    "external_user_name": external_user_name,
                    "post_id": post_id,
                    "post_is_sensitive": post_is_sensitive,
                    "message_text": guard.sanitized_text,
                    "detected_intent": intent,
                    "confidence": confidence,
                    "policy_action": decision.action.value,
                    "assigned_role": None,
                    "proposed_response": response,
                    "flagged_reasons": flagged,
                    "status": "approved",
                    "final_response": response,
                    "trace_id": uuid.uuid4().hex[:12],
                    "created_at": _now_iso(),
                    "event_at": _event_time_iso(timestamp),
                    "expires_at": None,
                }
            )
        else:
            # Flag OFF: auto-able nhưng chưa được phép gửi → pending cho QL
            # duyệt tay (ADR-008: người quyết). KHÔNG ghi auto_sent.
            review_id = fb_review_insert(
                {
                    "source": source,
                    "external_thread_id": message_id if source == "comment" else f"fb_{psid}",
                    "external_psid": psid,
                    "external_user_name": external_user_name,
                    "post_id": post_id,
                    "post_is_sensitive": post_is_sensitive,
                    "message_text": guard.sanitized_text,
                    "detected_intent": intent,
                    "confidence": confidence,
                    "policy_action": decision.action.value,
                    "assigned_role": "quan_ly",
                    "proposed_response": response,
                    "flagged_reasons": flagged + ["auto_blocked_by_flag"],
                    "status": "pending",
                    "trace_id": uuid.uuid4().hex[:12],
                    "created_at": _now_iso(),
                    "event_at": _event_time_iso(timestamp),
                    "expires_at": _sla_expiry(10),
                }
            )

    audit_add(
        _now_iso(),
        "fb_policy_engine",
        decision.action.value,
        {
            "psid": psid, "intent": intent, "confidence": confidence,
            "reason": decision.reason, "review_id": review_id,
        },
    )
    return {
        "action": decision.action.value,
        "review_id": review_id,
        "response": response,
        "intent": intent,
        "confidence": confidence,
        "reason": decision.reason,
        "flagged_reasons": flagged,
    }


def _audit_block(psid: str, text: str, loai: str, reason: str) -> None:
    audit_add(_now_iso(), "fb_moderation_block", loai, {
        "psid": psid, "reason": reason, "text_len": len(text),
    })
