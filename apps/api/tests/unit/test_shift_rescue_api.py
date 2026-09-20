"""Shift Rescue API tests (Phase 03)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from ca_api.interfaces.http.shift_rescue import clear_shift_rescue_state
from ca_api.persist import init_db
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    clear_shift_rescue_state()


def _intake(role: str = "lan") -> dict:
    r = client.post(
        "/api/v1/experience/shift-rescue/intake",
        json={
            "case_id": "rescue_e2e_1",
            "absence_nv_id": "nv_absent_quan",
            "shift_id": "t7_toi",
            "reason": "Ốm đột xuất",
        },
        headers=headers(client, role),
    )
    return r


def test_intake_requires_manager() -> None:
    r = _intake(role="minh")
    assert r.status_code == 403


def test_intake_creates_case() -> None:
    r = _intake()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "reported"
    assert body["shift_id"] == "t7_toi"
    assert body["replayable"] is True


def test_intake_unknown_shift_422() -> None:
    r = client.post(
        "/api/v1/experience/shift-rescue/intake",
        json={"case_id": "c", "absence_nv_id": "nv_1", "shift_id": "khong_co"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 422


def test_intake_missing_fields_422() -> None:
    r = client.post(
        "/api/v1/experience/shift-rescue/intake",
        json={"case_id": "c"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 422


def test_candidates_generated() -> None:
    case_id = _intake().json()["case_id"]
    r = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/candidates",
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "candidates_ready"
    # Ít nhất 1 safe + 1 blocked (người thiếu kỹ năng)
    assert len(body["candidates"]) >= 1
    assert any(c["safe"] for c in body["candidates"])


def test_candidates_not_found() -> None:
    r = client.post(
        "/api/v1/experience/shift-rescue/khong_co/candidates",
        headers=headers(client, "lan"),
    )
    assert r.status_code == 404


def test_propose_only_safe() -> None:
    case_id = _intake().json()["case_id"]
    client.post(f"/api/v1/experience/shift-rescue/{case_id}/candidates", headers=headers(client, "lan"))
    cand = client.get(f"/api/v1/experience/shift-rescue/{case_id}", headers=headers(client, "lan")).json()["candidates"][0]

    # propose candidate blocked → 409
    bad = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/propose",
        json={"candidate_id": "cand_khong_an_toan"},
        headers=headers(client, "lan"),
    )
    assert bad.status_code == 409

    good = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/propose",
        json={"candidate_id": cand["candidate_id"]},
        headers=headers(client, "lan"),
    )
    assert good.status_code == 200, good.text


def test_invite_idempotent() -> None:
    case_id = _intake().json()["case_id"]
    client.post(f"/api/v1/experience/shift-rescue/{case_id}/candidates", headers=headers(client, "lan"))
    candidates = client.get(f"/api/v1/experience/shift-rescue/{case_id}", headers=headers(client, "lan")).json()["candidates"]
    ids = [c["candidate_id"] for c in candidates[:1]]

    r1 = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/invite",
        json={"candidate_ids": ids},
        headers=headers(client, "lan"),
    )
    r2 = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/invite",
        json={"candidate_ids": ids},
        headers=headers(client, "lan"),
    )
    assert r1.json()["invited"] == r2.json()["invited"]
    assert len(r1.json()["invited"]) == 1


def test_confirm_stale_snapshot_409() -> None:
    case_id = _intake().json()["case_id"]
    client.post(f"/api/v1/experience/shift-rescue/{case_id}/candidates", headers=headers(client, "lan"))
    cand = client.get(f"/api/v1/experience/shift-rescue/{case_id}", headers=headers(client, "lan")).json()["candidates"][0]
    client.post(f"/api/v1/experience/shift-rescue/{case_id}/propose", json={"candidate_id": cand["candidate_id"]}, headers=headers(client, "lan"))
    client.post(f"/api/v1/experience/shift-rescue/{case_id}/invite", json={"candidate_ids": [cand["candidate_id"]]}, headers=headers(client, "lan"))
    client.post(f"/api/v1/experience/shift-rescue/{case_id}/respond", json={"candidate_id": cand["candidate_id"], "accept": True}, headers=headers(client, "lan"))

    # Giả lập stale: sửa snapshot hash trong case.
    from ca_api.interfaces.http.shift_rescue import _CASES

    _CASES[case_id]["command"]["schedule_snapshot_hash"] = "stale_hash"
    r = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/confirm",
        json={"candidate_id": cand["candidate_id"]},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 409


def test_confirm_employee_forbidden() -> None:
    case_id = _intake().json()["case_id"]
    r = client.post(
        f"/api/v1/experience/shift-rescue/{case_id}/confirm",
        json={"candidate_id": "x"},
        headers=headers(client, "minh"),
    )
    assert r.status_code == 403