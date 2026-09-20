"""Spatial memory grounding tests (Phase 05)."""

from __future__ import annotations

from ca_agents.ag_spatial_memory.grounding import (
    GroundingContext,
    build_grounded_answer,
    qualify_claim,
)
from ca_contracts import (
    ExperienceMemory,
    MemoryConsentStatus,
    MemoryStatus,
    MemoryVisibility,
)


def _confirmed(content: str, memory_id: str = "m1") -> ExperienceMemory:
    return ExperienceMemory(
        memory_id=memory_id,
        anchor_id="bar",
        owner_scope="nv",
        content=content,
        consent_status=MemoryConsentStatus.GRANTED,
        visibility=MemoryVisibility.STAFF,
        status=MemoryStatus.CONFIRMED,
    )


def test_grounded_answer_from_confirmed_memory() -> None:
    ctx = GroundingContext(memories=[_confirmed("khách thích ít ngọt")])
    ans = build_grounded_answer("khách thích gì?", ctx)
    assert ans.grounded
    assert "ít ngọt" in ans.answer_text
    assert ans.citations == ["m1"]


def test_no_confirmed_memory_no_hallucination() -> None:
    ctx = GroundingContext(memories=[_confirmed("x", memory_id="draft1")])
    # chỉ draft → không coi là confirmed
    ctx.memories[0].status = MemoryStatus.DRAFT
    ans = build_grounded_answer("chuyện gì đã xảy ra?", ctx)
    assert not ans.grounded
    assert "Chưa có ký ức đã xác nhận" in ans.answer_text


def test_absolute_claim_qualified_or_rejected() -> None:
    ctx = GroundingContext(memories=[_confirmed("khách thích ít ngọt")])
    ok, reason = qualify_claim("tất cả khách chắc chắn thích ít ngọt", ctx)
    assert not ok
    assert "tuyệt đối" in reason


def test_claim_mismatch_rejected() -> None:
    ctx = GroundingContext(memories=[_confirmed("khách thích trà")])
    ok, reason = qualify_claim("khách bị dị ứng hải sản", ctx)
    assert not ok
    assert "không khớp" in reason


def test_grounded_answer_lists_unsupported_claims() -> None:
    ctx = GroundingContext(memories=[_confirmed("khách thích trà")])
    ans = build_grounded_answer("khách bị dị ứng hải sản chắc chắn", ctx)
    # Claim tuyệt đối bị đánh dấu unsupported nhưng câu trả lời vẫn giữ nguồn confirmed.
    assert ans.unsupported_claims
    assert "tuyệt đối" in ans.unsupported_claims[0]
    # grounded vẫn True vì câu trả lời dựa trên memory confirmed — claim phóng đại
    # nằm ở unsupported_claims (không biến mất âm thầm).
    assert ans.grounded is True