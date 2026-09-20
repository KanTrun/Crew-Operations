"""Ranh giới API Grand AI Experience (plan 260920-1442 Phase 01).

Test: capabilities theo vai trò, map read-only, replay deterministic,
unauthorized bị chặn, không mở mạng.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ca_api.interfaces.http.main import app
from ca_api.persist import init_db
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "data" / "fixtures" / "grand_experience"


@pytest.fixture(autouse=True)
def _replay_env(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    monkeypatch.delenv("NHIPQUAN_EXPERIENCE_READ_ADAPTER", raising=False)


def test_capabilities_requires_auth() -> None:
    r = client.get("/api/v1/experience/capabilities")
    assert r.status_code == 401


def test_capabilities_manager() -> None:
    r = client.get("/api/v1/experience/capabilities", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "quan_ly"
    caps = set(body["capabilities"])
    assert "experience.read" in caps
    assert "experience.simulate" in caps
    assert "experience.confirm" in caps


def test_capabilities_employee_no_confirm() -> None:
    r = client.get("/api/v1/experience/capabilities", headers=headers(client, "minh"))
    assert r.status_code == 200, r.text
    caps = set(r.json()["capabilities"])
    assert "experience.read" in caps
    assert "experience.confirm" not in caps
    assert "experience.simulate" not in caps


def test_map_read_only_with_anchors() -> None:
    r = client.get("/api/v1/experience/map", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["anchors"]) >= 8
    ids = {a["anchor_id"] for a in body["anchors"]}
    assert {"bar", "cashier", "blender-02"} <= ids
    assert body["data_quality"][0]["code"] == "fixture_replay"


def test_map_requires_auth() -> None:
    r = client.get("/api/v1/experience/map")
    assert r.status_code == 401


def test_events_filter_by_anchor() -> None:
    r = client.get(
        "/api/v1/experience/events",
        params={"anchor_id": "blender-02"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] >= 1
    assert all(e["anchor_id"] == "blender-02" for e in body["events"])


def test_events_unknown_type_rejected_read_boundary() -> None:
    """Kiểu sự kiện lạ phải fail-closed ngay ở contract (không trả "unknown")."""
    from ca_contracts import ExperienceEvent
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ExperienceEvent(
            event_id="e1",
            event_type="loai_lạ",
            occurred_at="2026-09-18T08:00:00+07:00",
            source="replay",
        )


def test_snapshot_hash_stable_across_requests() -> None:
    h1 = client.get("/api/v1/experience/snapshot-hash", headers=headers(client, "lan"))
    h2 = client.get("/api/v1/experience/snapshot-hash", headers=headers(client, "lan"))
    assert h1.status_code == 200, h1.text
    assert h2.status_code == 200, h2.text
    assert h1.json()["snapshot_hash"] == h2.json()["snapshot_hash"]
    assert len(h1.json()["snapshot_hash"]) == 64


def test_replay_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replay không mở socket — fixture đọc local, không gọi ngoài."""
    import socket

    def _deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("network blocked in replay")

    monkeypatch.setattr(socket, "create_connection", _deny)
    r = client.get("/api/v1/experience/map", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text


def test_fixture_has_no_secret_patterns() -> None:
    """Fixture không chứa secret/token/audio/real data."""
    bad_patterns = ("sk-", "token=", "password", "Bearer ", "-----BEGIN")
    for path in FIXTURE_DIR.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        for bad in bad_patterns:
            assert bad.lower() not in text, f"{path.name} chứa pattern {bad}"