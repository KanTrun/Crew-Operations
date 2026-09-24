"""Ranking — chính sách xếp hạng tất định theo thứ tự ưu tiên (policy versioned).

Lexicographic ordering (plan Phase 03):
1. hard-feasible only (đã lọc trước ở eligibility)
2. required skill coverage (ưu tiên đúng kỹ năng)
3. least fairness debt increase
4. least added hours
5. least schedule disruption (ít ca đang giữ)
6. stable staff ID tie-breaker

Ranking KHÔNG phải LLM judgment. Mỗi thành phần + weight được expose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RANKING_POLICY_VERSION = "v1"


@dataclass(frozen=True)
class RankedCandidate:
    """Một ứng viên đã xếp hạng (chỉ chứa thông tin tối thiểu an toàn)."""

    nv_id: str
    nv_ten: str
    safe: bool
    fairness_delta: float
    added_hours: float
    skill_coverage: dict[str, bool]
    reason_passes: list[str]
    reason_blocks: list[str]
    rank: int


def _coverage_score(skills: set[str], required: str | None) -> int:
    if not required:
        return 0
    return 1 if required in skills else 0


def rank_candidates(
    safe_staff: list[Any],
    *,
    required_skill: str | None,
    debt_by_nv: dict[str, dict[str, float]],
    hours_by_nv: dict[str, float],
    shift_count_by_nv: dict[str, int],
    policy_version: str = RANKING_POLICY_VERSION,
) -> list[RankedCandidate]:
    """Xếp hạng danh sách an toàn theo policy. Trả kèm lý do từng phần.

    `safe_staff` là list StaffProfile đã qua filter_eligible (an toàn).
    Không bao giờ nhận người vi phạm hard constraint vào đây.
    """
    ordered: list[dict[str, Any]] = []
    for s in safe_staff:
        nv_id = s.nv_id
        debt = debt_by_nv.get(nv_id, {})
        fairness_total = sum(debt.values())
        ordered.append(
            {
                "profile": s,
                "coverage": _coverage_score(s.ky_nang, required_skill),
                "fairness_delta": fairness_total,
                "added_hours": hours_by_nv.get(nv_id, 0.0),
                "disruption": shift_count_by_nv.get(nv_id, 0),
                "nv_id": nv_id,
            }
        )

    # Lexicographic đúng thứ tự: coverage > fairness > hours > disruption > id
    ordered.sort(
        key=lambda r: (
            -r["coverage"],
            r["fairness_delta"],
            r["added_hours"],
            r["disruption"],
            r["nv_id"],
        )
    )

    result: list[RankedCandidate] = []
    for idx, r in enumerate(ordered, start=1):
        profile: Any = r["profile"]
        result.append(
            RankedCandidate(
                nv_id=r["nv_id"],
                nv_ten=getattr(profile, "ten", "") or "",
                safe=True,
                fairness_delta=float(r["fairness_delta"]),
                added_hours=float(r["added_hours"]),
                skill_coverage={required_skill or "": bool(r["coverage"])},
                reason_passes=[
                    "hard_constraints_ok",
                    f"fairness_delta={r['fairness_delta']:.2f}",
                    f"added_hours={r['added_hours']}",
                    f"policy_version={policy_version}",
                ],
                reason_blocks=[],
                rank=idx,
            )
        )
    return result