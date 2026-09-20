"""Rule learning API tests (Phase 04)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.experience_rules import clear_rule_state
from ca_api.interfaces.http.main import app
from ca_api.persist import init_db
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    clear_rule_state()


def _discover_and_get_candidate() -> str:
    d = client.post("/api/v1/experience/rules/discover", headers=headers(client, "lan"))
    assert d.status_code == 200, d.text
    c = client.get("/api/v1/experience/rules/candidates", headers=headers(client, "lan"))
    cands = c.json()["candidates"]
    assert cands, "phải có candidate từ fixture 3 tín hiệu"
    return cands[0]["candidate_id"]


def test_discover_requires_manager() -> None:
    r = client.post("/api/v1/experience/rules/discover", headers=headers(client, "minh"))
    assert r.status_code == 403


def test_discover_finds_candidate() -> None:
    r = client.post("/api/v1/experience/rules/discover", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    assert r.json()["count"] >= 1
    assert r.json()["sources"] == "fixture_replay"


def test_candidates_list_after_discover() -> None:
    _discover_and_get_candidate()
    r = client.get("/api/v1/experience/rules/candidates", headers=headers(client, "lan"))
    assert r.status_code == 200
    assert len(r.json()["candidates"]) >= 1


def test_evidence_timeline() -> None:
    cid = _discover_and_get_candidate()
    r = client.get(f"/api/v1/experience/rules/{cid}/evidence", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["repeated_decisions"] >= 3
    assert body["actors"]


def test_evidence_not_found() -> None:
    r = client.get("/api/v1/experience/rules/khong_co/evidence", headers=headers(client, "lan"))
    assert r.status_code == 404


def test_shadow_test_reproducible() -> None:
    cid = _discover_and_get_candidate()
    a = client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    b = client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    assert a.status_code == 200, a.text
    assert a.json()["shadow"] == b.json()["shadow"]


def test_confirm_requires_shadow_first() -> None:
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan"))
    assert r.status_code == 409  # chưa shadow


def test_confirm_after_shadow() -> None:
    cid = _discover_and_get_candidate()
    client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    r = client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    assert r.json()["not_auto_activated"] is True


def test_reject_candidate() -> None:
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/reject", headers=headers(client, "lan"))
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_employee_cannot_activate() -> None:
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "minh"))
    assert r.status_code == 403