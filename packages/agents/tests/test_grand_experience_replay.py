"""Replay tất định cho Grand AI Experience (plan 260920-1442 Phase 01).

Test các invariant: replay hai lần cho kết quả byte-equivalent, hash ổn định
khi JSON key order thay đổi, KHÔNG mở mạng khi replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ca_agents.grand_experience.adapter import resolve_experience_read_adapter
from ca_agents.grand_experience.replay import (
    FixtureReader,
    replay_fingerprint,
)
from ca_contracts import SpatialAnchor

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "data" / "fixtures" / "grand_experience"


@pytest.fixture(autouse=True)
def _replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    monkeypatch.delenv("NHIPQUAN_EXPERIENCE_READ_ADAPTER", raising=False)


def test_fixture_dir_exists() -> None:
    assert FIXTURE_DIR.is_dir(), f"thiếu fixture dir: {FIXTURE_DIR}"


def test_replay_twice_byte_equivalent() -> None:
    reader = FixtureReader(FIXTURE_DIR)
    first = reader.fingerprint()
    second = reader.fingerprint()
    assert first == second


def test_fingerprint_stable_when_key_order_changes() -> None:
    a = {"b": 1, "a": [{"x": 2, "y": 3}], "z": "text"}
    b = {"z": "text", "a": [{"y": 3, "x": 2}], "b": 1}
    assert replay_fingerprint(a) == replay_fingerprint(b)


def test_events_load_and_filter_by_anchor() -> None:
    reader = FixtureReader(FIXTURE_DIR)
    events = reader.list_events(anchor_id="blender-02")
    assert len(events) >= 1
    assert all(e["anchor_id"] == "blender-02" for e in events)


def test_events_filter_unknown_anchor_empty() -> None:
    reader = FixtureReader(FIXTURE_DIR)
    assert reader.list_events(anchor_id="khong_co") == []


def test_spatial_map_anchors_valid() -> None:
    reader = FixtureReader(FIXTURE_DIR)
    anchors = reader.list_anchors()
    assert anchors
    for a in anchors:
        assert isinstance(a, SpatialAnchor)
        assert a.anchor_id
        assert a.kind


def test_adapter_replay_default_is_fixture() -> None:
    adapter = resolve_experience_read_adapter()
    assert isinstance(adapter, FixtureReader)
    assert adapter.list_anchors()


def test_adapter_fingerprint_nonempty() -> None:
    reader = FixtureReader(FIXTURE_DIR)
    assert len(reader.fingerprint()) == 64


def test_replay_no_network_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture reader không mở socket — monkeypatch requests để chứng minh."""
    adapter = resolve_experience_read_adapter()
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert adapter.list_anchors()
    assert adapter.list_events()


def test_replay_session_is_deterministic_across_processes() -> None:
    """Chạy lại cùng input (fixture) → cùng fingerprint (ADR-002)."""
    reader = FixtureReader(FIXTURE_DIR)
    fp1 = reader.fingerprint()
    # Tạo reader mới (mô phỏng process mới) → hash phải giữ nguyên.
    fp2 = FixtureReader(FIXTURE_DIR).fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 64
    # Fingerprint phản ánh fixture; thay đổi fixture sẽ làm đỏ test (đúng vậy).
    assert fp1 != replay_fingerprint({})