"""Rule learning discover tests (Phase 04)."""

from __future__ import annotations

from ca_agents.ag_rule_learning.discover import (
    DecisionSignal,
    discover_rule_candidates,
    group_decisions,
)

SNAP = "snap_rule_20260918_1234abcd"


def _signal(i: int, decision: str = "them_nguoi_gio_cao", *, outcome: str = "ok", day_part: str = "toi") -> DecisionSignal:
    return DecisionSignal(
        signal_id=f"sig_{i}",
        decision=decision,
        day_part=day_part,
        station="bar",
        skill="pha_che",
        demand_band="cao",
        outcome=outcome,
    )


def test_two_decisions_not_enough_evidence() -> None:
    sigs = [_signal(1), _signal(2)]
    assert discover_rule_candidates(sigs, snapshot_hash=SNAP) == []


def test_three_decisions_create_candidate() -> None:
    sigs = [_signal(1), _signal(2), _signal(3)]
    candidates = discover_rule_candidates(sigs, snapshot_hash=SNAP)
    assert len(candidates) == 1
    c = candidates[0]
    assert len(c.evidence_refs) == 3
    assert c.condition["day_part"] == "toi"
    assert c.created_from_snapshot_hash == SNAP


def test_counterexample_marks_candidate() -> None:
    sigs = [_signal(1, outcome="ok"), _signal(2, outcome="ok"), _signal(3, outcome="reject")]
    candidates = discover_rule_candidates(sigs, snapshot_hash=SNAP)
    assert len(candidates) == 1
    assert len(candidates[0].counterexample_refs) >= 1


def test_grouping_stable_id() -> None:
    a = discover_rule_candidates([_signal(1), _signal(2), _signal(3)], snapshot_hash=SNAP)
    b = discover_rule_candidates([_signal(1), _signal(2), _signal(3)], snapshot_hash=SNAP)
    assert a[0].candidate_id == b[0].candidate_id


def test_unknown_condition_not_invented() -> None:
    """Condition phải từ registry — không nhận key lạ."""
    for grp in group_decisions([_signal(1), _signal(2), _signal(3)]):
        for key in grp["condition"]:
            assert key in {"day_part", "station", "skill", "demand_band", "absence_type"}


def test_mixed_groups_split() -> None:
    """Khác day_part → group khác → candidate khác."""
    sigs = [_signal(1, day_part="toi"), _signal(2, day_part="toi"), _signal(3, day_part="toi"), _signal(4, day_part="sang"), _signal(5, day_part="sang"), _signal(6, day_part="sang")]
    candidates = discover_rule_candidates(sigs, snapshot_hash=SNAP)
    assert len(candidates) == 2