"""Tour planner — chuỗi anchor đóng, narration grounded (không LLM thêm fact)."""

from __future__ import annotations

from ca_contracts import (
    ExperienceMemory,
    TourPlan,
    TourStep,
)

# Route mở quán mặc định (deterministic, closed graph)
OPENING_ROUTE = [
    ("entrance", "Cửa vào — nơi đón khách đầu tiên"),
    ("bar", "Quầy pha chế — trái tim đồ uống"),
    ("cashier", "Quầy thu ngân — thanh toán và hỗ trợ"),
    ("espresso-machine-01", "Máy pha cà phê chính"),
    ("window_table", "Bàn cửa sổ — khu vực khách ngồi"),
]


def plan_tour(
    route: list[tuple[str, str]] | None = None,
    memories: list[ExperienceMemory] | None = None,
) -> TourPlan:
    """Dựng tour từ route đóng + memory confirmed để narration grounded.

    Nếu một step thiếu memory confirmed thì narration vẫn dùng mô tả anchor
    (không bịa sự kiện) và citation rỗng.
    """
    steps: list[TourStep] = []
    confirmed = [
        m for m in (memories or []) if m.status.value == "confirmed"
    ]
    for idx, (anchor_id, desc) in enumerate((route or OPENING_ROUTE), start=1):
        related = [m for m in confirmed if m.anchor_id == anchor_id]
        citation_ids = [m.memory_id for m in related[:3]]
        narrative = desc
        if related:
            extra = "; ".join(m.content for m in related[:2])
            narrative = f"{desc}. Ký ức: {extra}"
        steps.append(
            TourStep(
                step_id=f"step_{idx:02d}",
                anchor_id=anchor_id,
                narrative=narrative,
                citation_memory_ids=citation_ids,
            )
        )
    return TourPlan(tour_id="tour_chao_doi", steps=steps, grounded=True)