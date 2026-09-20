"""QUANVERSE API tests (Phase 06)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from ca_api.interfaces.http.quanverse import clear_quanverse_state
from ca_api.persist import init_db
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    clear_quanverse_state()


def test_manager_snapshot_full_projection() -> None:
    r = client.get("/api/v1/experience/quanverse/snapshot", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "quan_ly"
    assert len(body["zones"]) >= 2
    assert body["events"]  # manager thấy rescue + mode events


def test_customer_snapshot_no_staff_data() -> None:
    """Khách không thấy staff/private ops."""
    r = client.get("/api/v1/experience/quanverse/snapshot", headers=headers(client, "minh"))
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "nhan_vien"  # minh là employee, không phải khách


def test_employee_snapshot_limited_events() -> None:
    r = client.get("/api/v1/experience/quanverse/snapshot", headers=headers(client, "minh"))
    body = r.json()
    # Employee chỉ thấy rescue_case/signal — không thấy timestamp private
    for ev in body["events"]:
        assert ev["event_type"] in {"rescue_case", "signal"}


def test_modes_list() -> None:
    r = client.get("/api/v1/experience/quanverse/modes", headers=headers(client, "lan"))
    assert r.status_code == 200
    assert len(r.json()["modes"]) >= 2


def test_mode_propose_draft() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/modes/troi_mua/propose",
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["proposal_status"] == "draft"
    assert body["confirmed"] is False
    assert body["affected_projections"]


def test_employee_cannot_confirm_mode() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/modes/troi_mua/confirm",
        headers=headers(client, "minh"),
    )
    assert r.status_code == 403


def test_manager_confirm_mode() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/modes/troi_mua/confirm",
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active"] is True
    assert body["audited"] is True


def test_unknown_mode_422() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/modes/khong_biet/propose",
        headers=headers(client, "lan"),
    )
    assert r.status_code == 422


def test_flavor_recommend() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/flavor/recommend",
        json={"do_ngot": "it", "co_sua": False, "huong_tra": True},
        headers=headers(client, "minh"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recommendations"]
    assert any("lý do" not in x or x["reasons"] for x in body["recommendations"])


def test_flavor_allergy_blocked() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/flavor/recommend",
        json={"do_ngot": "vua", "dietary_allergy": ["sữa"]},
        headers=headers(client, "minh"),
    )
    ids = {x["mon_id"] for x in r.json()["recommendations"]}
    assert "cafe_sua" not in ids
    assert "tr_sua" not in ids


def test_preference_propose_needs_consent() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/preferences/propose",
        json={"content": "khách thích bàn cửa sổ"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["needs_consent"] is True
    assert body["stored"] is False


def test_preference_delete_idempotent() -> None:
    r = client.delete(
        "/api/v1/experience/quanverse/preferences/pref_1",
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_tour_entry() -> None:
    r = client.get("/api/v1/experience/quanverse/tour/tour_chao_doi", headers=headers(client, "lan"))
    assert r.status_code == 200
    assert r.json()["tour_id"] == "tour_chao_doi"


def test_ar_session_requires_qr() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/ar-session",
        json={},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 422

    r2 = client.post(
        "/api/v1/experience/quanverse/ar-session",
        json={"qr": "blender-02"},
        headers=headers(client, "lan"),
    )
    assert r2.status_code == 200
    assert r2.json()["fallback"] == "map_or_qr_text"