"""Grounding — hợp lệ hoá yêu cầu LLM; từ chối/điều kiện hoá claim không nguồn.

LLM chỉ diễn đạt câu chữ, không thêm sự kiện chưa có nguồn. Grounding gate
kiểm tra mọi claim phải có memory_id/event ref tương ứng.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ca_contracts import (
    ExperienceMemory,
    GroundedAnswer,
    MemoryProposal,
)


@dataclass
class GroundingContext:
    """Packet ngữ cảnh grounded cho câu trả lời."""

    memories: list[ExperienceMemory] = field(default_factory=list)
    event_refs: list[str] = field(default_factory=list)


# Từ khoá claim có thể không có nguồn → cần đánh dấu
_UNSUPPORTED_HINTS = (
    "chắc chắn", "luôn luôn", "tất cả khách", "không bao giờ", "100%"
)


def qualify_claim(
    sentence: str,
    context: GroundingContext,
) -> tuple[bool, str]:
    """Qualify một claim: True nếu grounded, False + lý do nếu không.

    - Claim phải khớp ít nhất một memory đã confirm có trong context.
    - Từ khoá tuyệt đối (chắc chắn/luôn luôn...) bị nghi ngờ → không grounded
      trừ khi memory confirm tường minh.
    """
    low = sentence.lower()
    for hint in _UNSUPPORTED_HINTS:
        if hint in low:
            return False, f"claim tuyệt đối không được phép: {hint}"
    confirmed = [m for m in context.memories if m.status.value == "confirmed"]
    if not confirmed:
        return False, "không có ký ức đã xác nhận trong ngữ cảnh"
    # Claim phải khớp ý: ≥2 token dài (>3 ký tự) chung với một memory confirmed.
    claim_tokens = {t for t in low.split() if len(t) > 3}
    for mem in confirmed:
        mem_tokens = {t for t in mem.content.lower().split() if len(t) > 3}
        overlap = claim_tokens & mem_tokens
        if len(overlap) >= 2:
            return True, ""
    return False, "claim không khớp ký ức đã xác nhận"


def build_grounded_answer(
    question: str,
    context: GroundingContext,
    *,
    proposal: MemoryProposal | None = None,
) -> GroundedAnswer:
    """Dựng câu trả lời grounded: dùng memory confirmed, citations, các
    unsupported claims được liệt kê rõ — KHÔNG bịa nội dung."""

    confirmed = [m for m in context.memories if m.status.value == "confirmed"]
    memories_text = " ".join(
        f"[{m.memory_id}] {m.content}" for m in confirmed
    )
    if memories_text:
        response = (
            "Theo ký ức đã xác nhận tại quán: "
            + "; ".join(m.content for m in confirmed)
        )
        grounded = True
    else:
        response = "Chưa có ký ức đã xác nhận cho khu vực này. (Không suy đoán nội dung.)"
        grounded = False

    # Qualify claim đặt câu hỏi: nếu có từ tuyệt đối thì đánh dấu unsupported
    # (nhưng không rớt câu trả lời grounded đã có nguồn).
    unsupported: list[str] = []
    ok_grounded, reason = qualify_claim(question, context)
    if not ok_grounded:
        unsupported.append(reason)
        # Câu trả lời vẫn grounded nếu dựa trên memory confirmed; chỉ claim
        # phóng đại bị đánh dấu.
        if grounded:
            unsupported = [r for r in unsupported if "tuyệt đối" in r]

    return GroundedAnswer(
        answer_id=f"ans_{abs(hash(question)) % 100000:06d}",
        answer_text=response,
        citations=[m.memory_id for m in confirmed],
        memory_ids=[m.memory_id for m in confirmed],
        proposal_id=proposal.proposal_id if proposal else None,
        unsupported_claims=unsupported,
        grounded=grounded,
    )