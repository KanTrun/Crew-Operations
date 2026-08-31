from __future__ import annotations

import pytest
from ca_gates import (
    compute_snapshot_hash,
    validate_scope,
    validate_stale,
)


def test_vf_scope_same_store_manager() -> None:
    res = validate_scope(
        caller_store_id="quan_01",
        target_store_id="quan_01",
        caller_role="quan_ly",
        intent="SCHEDULE_SOLVE",
    )
    assert res.passed is True
    assert res.blocked is False


def test_vf_scope_cross_store_forbidden() -> None:
    res = validate_scope(
        caller_store_id="quan_01",
        target_store_id="quan_02",
        caller_role="quan_ly",
        intent="SCHEDULE_SOLVE",
    )
    assert res.passed is False
    assert res.blocked is True
    assert "cross_store_forbidden" in res.reason


def test_vf_scope_insufficient_role_staff_for_privileged() -> None:
    res = validate_scope(
        caller_store_id="quan_01",
        target_store_id="quan_01",
        caller_role="nhan_vien",
        intent="SCHEDULE_SOLVE",
    )
    assert res.passed is False
    assert res.blocked is True
    assert "insufficient_role" in res.reason


def test_vf_scope_staff_for_public_intent() -> None:
    res = validate_scope(
        caller_store_id="quan_01",
        target_store_id="quan_01",
        caller_role="nhan_vien",
        intent="QUERY_SOP",
    )
    assert res.passed is True
    assert res.blocked is False


def test_vf_stale_matching_hash() -> None:
    data1 = {"shifts": ["c1", "c2"]}
    h = compute_snapshot_hash(data1)
    res = validate_stale(draft_snapshot_hash=h, current_snapshot_hash=h)
    assert res.passed is True
    assert res.stale is False


def test_vf_stale_diverged_hash() -> None:
    h1 = compute_snapshot_hash({"shifts": ["c1", "c2"]})
    h2 = compute_snapshot_hash({"shifts": ["c1", "c2", "c3"]})
    res = validate_stale(draft_snapshot_hash=h1, current_snapshot_hash=h2)
    assert res.passed is False
    assert res.stale is True
    assert "data_stale_mismatch" in res.reason
