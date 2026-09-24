"""Shift Rescue ranking tests (Phase 03)."""

from __future__ import annotations

from ca_agents.ag_shift_rescue.eligibility import StaffProfile
from ca_agents.ag_shift_rescue.ranking import (
    RANKING_POLICY_VERSION,
    rank_candidates,
)


def _s(nv_id: str, skills: set[str]) -> StaffProfile:
    return StaffProfile(nv_id=nv_id, ten=f"NV {nv_id}", ky_nang=skills)


def test_ranking_prioritizes_skill_coverage() -> None:
    staff = [
        _s("nv_b", {"phuc_vu"}),
        _s("nv_a", {"pha_che", "phuc_vu"}),
    ]
    ranked = rank_candidates(
        staff,
        required_skill="pha_che",
        debt_by_nv={},
        hours_by_nv={},
        shift_count_by_nv={},
    )
    assert ranked[0].nv_id == "nv_a"  # có kỹ năng cần


def test_ranking_fairness_before_hours() -> None:
    staff = [_s("nv_low_debt", {"pha_che"}), _s("nv_high_debt", {"pha_che"})]
    ranked = rank_candidates(
        staff,
        required_skill="pha_che",
        debt_by_nv={
            "nv_low_debt": {"gio": 1.0},
            "nv_high_debt": {"gio": 9.0},
        },
        hours_by_nv={"nv_low_debt": 30.0, "nv_high_debt": 10.0},
        shift_count_by_nv={},
    )
    # Ít nợ công bằng hơn nên đứng trước dù nhiều giờ hơn
    assert ranked[0].nv_id == "nv_low_debt"


def test_ranking_stable_tie_breaker_by_id() -> None:
    staff = [_s("nv_b", {"pha_che"}), _s("nv_a", {"pha_che"})]
    ranked = rank_candidates(
        staff,
        required_skill="pha_che",
        debt_by_nv={},
        hours_by_nv={},
        shift_count_by_nv={},
    )
    assert ranked[0].nv_id == "nv_a"  # id sort ổn định


def test_ranking_reason_contains_policy_version() -> None:
    staff = [_s("nv_1", {"pha_che"})]
    ranked = rank_candidates(
        staff,
        required_skill="pha_che",
        debt_by_nv={},
        hours_by_nv={},
        shift_count_by_nv={},
    )
    assert any(RANKING_POLICY_VERSION in r for r in ranked[0].reason_passes)


def test_ranking_all_safe() -> None:
    staff = [_s("nv_1", {"pha_che"}), _s("nv_2", {"pha_che"})]
    ranked = rank_candidates(
        staff,
        required_skill="pha_che",
        debt_by_nv={},
        hours_by_nv={},
        shift_count_by_nv={},
    )
    assert all(r.safe for r in ranked)
    assert len(ranked) == 2