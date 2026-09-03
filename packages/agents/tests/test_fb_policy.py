"""Unit tests for fb_policy — every branch of the moderation matrix (plan §3.2).

Deterministic: no LLM, no I/O, no system clock (ADR-002).
Priority order is asserted explicitly: escalate_owner > priority_review > queue > auto.
"""

from __future__ import annotations

import pytest
from ca_agents.fb_policy import (
    AUTO_THRESHOLD,
    PolicyContext,
    decide,
)
from ca_contracts import FbPolicyAction


def ctx(**overrides: object) -> PolicyContext:
    base: dict[str, object] = {
        "source": "messenger",
        "sensitive_post": False,
        "repeat_ask_count": 0,
        "kb_has_fact": True,
        "price_above_limit": False,
        "recent_messages": (),
    }
    base.update(overrides)
    return PolicyContext(**base)  # type: ignore[arg-type]


# ── 1. AUTO whitelist ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("intent", "conf"),
    [("chao_hoi", 0.90), ("hoi_gio_dia_chi", 0.85), ("hoi_menu_gia", 0.85)],
)
def test_auto_at_exact_threshold(intent: str, conf: float) -> None:
    """Confidence == threshold (boundary) → auto_send."""
    d = decide(intent, conf, "xin chào quán ơi", ctx())
    assert d.action == FbPolicyAction.AUTO_SEND
    assert d.reason == "whitelisted_intent_confident"


@pytest.mark.parametrize(
    ("intent", "conf"),
    [("chao_hoi", 0.91), ("hoi_gio_dia_chi", 0.86), ("hoi_menu_gia", 0.90)],
)
def test_auto_above_threshold(intent: str, conf: float) -> None:
    d = decide(intent, conf, "quán mấy giờ đóng cửa ạ", ctx())
    assert d.action == FbPolicyAction.AUTO_SEND


@pytest.mark.parametrize(
    ("intent", "conf"),
    [("chao_hoi", 0.8999), ("hoi_gio_dia_chi", 0.8499), ("hoi_menu_gia", 0.8499)],
)
def test_queue_just_below_threshold(intent: str, conf: float) -> None:
    d = decide(intent, conf, "quán mấy giờ đóng cửa ạ", ctx())
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "below_auto_threshold"
    assert d.assigned_role == "quan_ly"
    assert d.sla_minutes == 10


def test_auto_threshold_table_matches_plan() -> None:
    """Threshold constants pinned to plan §3.2 — business decision, do not drift."""
    assert AUTO_THRESHOLD == {
        "chao_hoi": 0.90,
        "hoi_gio_dia_chi": 0.85,
        "hoi_menu_gia": 0.85,
    }


# ── 2. Mandatory-review intents ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "intent",
    ["hoi_khuyen_mai", "dat_ban", "tu_van_mon", "yeu_cau_dac_biet"],
)
def test_intent_requires_approval_even_high_confidence(intent: str) -> None:
    d = decide(intent, 0.99, "cho mình xem khuyến mãi với", ctx())
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "intent_requires_approval"
    assert d.assigned_role == "quan_ly"


def test_dat_ban_high_confidence_still_queue() -> None:
    d = decide("dat_ban", 0.95, "đặt bàn 10 người tối nay", ctx())
    assert d.action == FbPolicyAction.QUEUE_REVIEW


# ── 3. Complaints ────────────────────────────────────────────────────────────


def test_complaint_light_priority_review() -> None:
    d = decide("khieu_nai_gop_y", 0.90, "phục vụ chậm quá ạ", ctx())
    assert d.action == FbPolicyAction.PRIORITY_REVIEW
    assert d.assigned_role == "quan_ly"
    assert d.sla_minutes == 5


# ── 4. KB / price guards ─────────────────────────────────────────────────────


def test_fact_not_in_kb_queue() -> None:
    d = decide("hoi_gio_dia_chi", 0.95, "quán mở cửa mấy giờ", ctx(kb_has_fact=False))
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "fact_not_in_kb_or_price_limit"


def test_price_above_cap_queue() -> None:
    d = decide("hoi_menu_gia", 0.95, "combo tiệc giá bao nhiêu", ctx(price_above_limit=True))
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "fact_not_in_kb_or_price_limit"


def test_price_cap_not_applied_to_other_intents() -> None:
    d = decide("chao_hoi", 0.95, "chào quán", ctx(price_above_limit=True))
    assert d.action == FbPolicyAction.AUTO_SEND


# ── 5. Loop guard / low confidence / not whitelisted ─────────────────────────


def test_repeat_ask_loop_queues() -> None:
    d = decide("chao_hoi", 0.95, "hello", ctx(repeat_ask_count=3))
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "repeat_ask_loop"


def test_low_confidence_queues() -> None:
    d = decide("khac", 0.59, "ừ ừ được đấy", ctx())
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "low_confidence"


def test_confidence_boundary_060_exact_still_eligible_for_auto() -> None:
    """conf == 0.60 is NOT 'low' — falls through to whitelist check."""
    d = decide("khac", 0.60, "gì đó", ctx())
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "intent_not_whitelisted_for_auto"


def test_intent_not_whitelisted_for_auto() -> None:
    d = decide("khac", 0.80, "hôm nay trời đẹp nhỉ", ctx())
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "intent_not_whitelisted_for_auto"


# ── 6. Out of scope → block_polite ───────────────────────────────────────────


def test_out_of_scope_block_polite() -> None:
    d = decide("khac", 0.80, "quán ủng hộ chính trị đảng nào", ctx())
    assert d.action == FbPolicyAction.BLOCK_POLITE
    assert d.reason == "out_of_scope"


def test_out_of_scope_only_for_khac_intent() -> None:
    """Same keywords but complaint intent → complaint wins (priority order)."""
    d = decide("khieu_nai_gop_y", 0.80, "quán ủng hộ chính trị đảng nào", ctx())
    assert d.action == FbPolicyAction.PRIORITY_REVIEW


# ── 7. Owner escalation keywords (safety first — wins everything) ────────────


@pytest.mark.parametrize(
    "text",
    [
        "uống nước hôm qua bị ngộ độc quá",
        "cho xin hóa đơn đỏ công ty",
        "muốn gặp chủ quán trực tiếp",
        "bị dị ứng với nguyên liệu",
    ],
)
def test_owner_escalation_keyword_wins(text: str) -> None:
    d = decide("chao_hoi", 0.99, text, ctx())
    assert d.action == FbPolicyAction.ESCALATE_OWNER
    assert d.assigned_role == "chu_quan"
    assert d.sla_minutes == 15
    assert d.reason == "owner_escalation_keyword"


def test_owner_escalation_beats_heavy_complaint() -> None:
    """Two signals at once: 'ngộ độc' + '1 sao' → escalate wins (plan §6.4)."""
    d = decide(
        "khieu_nai_gop_y",
        0.85,
        "ngộ độc luôn rồi, tôi sẽ đánh 1 sao",
        ctx(),
    )
    assert d.action == FbPolicyAction.ESCALATE_OWNER


def test_owner_escalation_from_recent_messages() -> None:
    """Keyword split across messages in the same thread (plan §6.2d)."""
    d = decide(
        "khac",
        0.70,
        "hôm qua uống ở quán",
        ctx(recent_messages=("nước bị ngộ độc trong người quá",)),
    )
    assert d.action == FbPolicyAction.ESCALATE_OWNER


# ── 8. Evasion-resistance (normalize_text, plan §6.2c) ───────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "b.á.o  ch í nào đến phỏng vấn",        # chèn dấu chấm + khoảng trắng
        "baoo chi phỏng vấn quán",               # gõ dính
        "CHO XIN HÓA ĐƠN ĐỎ",                    # uppercase
        "hóa đơn đỏ  ạ",                         # double space
        "muốn gặp chủ  quán",                    # double space between words
    ],
)
def test_keyword_match_survives_evasion_and_case(text: str) -> None:
    d = decide("chao_hoi", 0.90, text, ctx())
    assert d.action == FbPolicyAction.ESCALATE_OWNER, f"evaded: {text}"


def test_no_accents_duplicate_keyword_list() -> None:
    """Plan §6.2c: keyword list must be single non-accented — assert a few."""
    from ca_agents.fb_policy import OWNER_ESCALATION_KEYWORDS

    for kw in OWNER_ESCALATION_KEYWORDS:
        assert kw == kw.lower()
        assert kw.isascii(), f"keyword should be non-accented ascii: {kw}"


def test_ambiguous_keyword_match_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keyword matches but classifier disagrees (intent=chao_hoi, kw='bao chi')
    → still escalate (deterministic) AND flag for quality review (plan §6.2c)."""
    d = decide("chao_hoi", 0.90, "cho quán lên báo chí quảng bá đi ạ", ctx())
    assert d.action == FbPolicyAction.ESCALATE_OWNER
    assert "keyword_matched_ambiguous" in d.flagged_reasons


def test_unambiguous_escalation_not_flagged_ambiguous() -> None:
    d = decide("khieu_nai_gop_y", 0.85, "bị ngộ độc quá", ctx())
    assert d.action == FbPolicyAction.ESCALATE_OWNER
    assert "keyword_matched_ambiguous" not in d.flagged_reasons


# ── 9. Comment source — stricter gate ────────────────────────────────────────


def test_comment_safe_intent_high_conf_auto() -> None:
    d = decide("hoi_gio_dia_chi", 0.95, "quán ở đâu vậy ạ", ctx(source="comment"))
    assert d.action == FbPolicyAction.AUTO_SEND


def test_comment_below_comment_threshold_queues() -> None:
    d = decide("hoi_gio_dia_chi", 0.90, "quán ở đâu vậy ạ", ctx(source="comment"))
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "comment_policy"
    assert d.sla_minutes == 15


def test_comment_unsafe_intent_never_auto() -> None:
    """hoi_menu_gia is whitelisted for messenger but NOT comment-safe."""
    d = decide("hoi_menu_gia", 0.99, "cà phê muối bao nhiêu tiền", ctx(source="comment"))
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "comment_policy"


def test_comment_sensitive_post_never_auto() -> None:
    d = decide("chao_hoi", 0.99, "chào quán", ctx(source="comment", sensitive_post=True))
    assert d.action == FbPolicyAction.QUEUE_REVIEW
    assert d.reason == "comment_policy"


# ── 10. Determinism & purity (ADR-002) ───────────────────────────────────────


def test_decide_is_pure_and_deterministic() -> None:
    """Same inputs → identical decision objects, no I/O, no clock."""
    a = decide("hoi_gio_dia_chi", 0.90, "quán mở mấy giờ", ctx())
    b = decide("hoi_gio_dia_chi", 0.90, "quán mở mấy giờ", ctx())
    assert a == b


def test_policy_context_defaults_immutable() -> None:
    from dataclasses import FrozenInstanceError

    c = ctx()
    with pytest.raises(FrozenInstanceError):
        c.source = "comment"  # type: ignore[misc]


def test_decision_contract_roundtrip() -> None:
    """PolicyDecision (from ca_contracts) validates per schema §3.4."""
    from ca_contracts import PolicyDecision as ContractDecision

    d = decide("chao_hoi", 0.95, "hi quán", ctx())
    contract = ContractDecision(
        action=d.action.value,
        reason=d.reason,
        intent=d.intent,
        confidence=d.confidence,
        assigned_role=d.assigned_role,
        sla_minutes=d.sla_minutes,
        flagged_reasons=list(d.flagged_reasons),
    )
    assert contract.action == "auto_send"
    assert 0.0 <= contract.confidence <= 1.0
