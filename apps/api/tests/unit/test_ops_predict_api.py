# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit & Integration tests cho Ops Predict API (plan 260918 mục 5)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _pin_replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")


def test_predict_run_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/ops/predict/run",
        json={
            "doanh_thu_by_ca": {
                "T2_sang": 100.0,
                "T2_chieu": 110.0,
                "T2_toi": 105.0,
                "T6_toi": 500.0,
                "T7_toi": 480.0,
            },
            "doanh_thu_by_mon": {},
            "ton_kho_by_time": {},
        },
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert isinstance(body["patterns"], list)
    assert isinstance(body["suggestions"], list)


def test_predict_suggestions_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.get("/api/v1/ops/predict/suggestions", headers=ql)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "suggestions" in body
    assert "patterns" in body


def test_twin_simulate_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/ops/twin/simulate",
        json={
            "scenario_id": "sc_test_1",
            "loai": "tang_gia",
            "tham_so": {
                "gia_cu": 25000,
                "gia_moi": 30000,
                "luong_ban_cu": 100,
                "chi_phi_bien_doi": 50000,
                "he_so_co_gian": -0.5,
            },
        },
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["scenario"]["loai"] == "tang_gia"
    assert "doanh_thu_moi" in body["scenario"]["ket_qua"]


def test_twin_scenarios_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.get("/api/v1/ops/twin/scenarios", headers=ql)
    assert res.status_code == 200, res.text
    assert "items" in res.json()


def test_approve_rule_not_found() -> None:
    ql = headers(client, "lan")
    res = client.post("/api/v1/ops/predict/rule_khong_co/approve", headers=ql)
    assert res.status_code == 404


def test_predict_requires_manager() -> None:
    # Nhân viên không có quyền chạy predict (chỉ Quản lý/Chủ quán)
    nv = headers(client, "minh")
    res = client.post(
        "/api/v1/ops/predict/run",
        json={"doanh_thu_by_ca": {}, "doanh_thu_by_mon": {}, "ton_kho_by_time": {}},
        headers=nv,
    )
    assert res.status_code == 403


def test_predict_run_idempotent() -> None:
    """Cùng payload → cùng kết quả (idempotency)."""
    from ca_api.interfaces.http.ops_predict import clear_rate_limits

    clear_rate_limits()
    ql = headers(client, "lan")
    payload = {
        "doanh_thu_by_ca": {
            "T2_sang": 100.0, "T2_chieu": 110.0, "T2_toi": 105.0,
            "T6_toi": 500.0, "T7_toi": 480.0,
        },
        "doanh_thu_by_mon": {},
        "ton_kho_by_time": {},
    }
    r1 = client.post("/api/v1/ops/predict/run", json=payload, headers=ql)
    r2 = client.post("/api/v1/ops/predict/run", json=payload, headers=ql)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["patterns"] == r2.json()["patterns"]


def test_twin_simulate_idempotent() -> None:
    from ca_api.interfaces.http.ops_predict import clear_rate_limits

    clear_rate_limits()
    ql = headers(client, "lan")
    payload = {
        "scenario_id": "sc_idem_1",
        "loai": "tang_gia",
        "tham_so": {
            "gia_cu": 25000, "gia_moi": 30000, "luong_ban_cu": 100,
            "chi_phi_bien_doi": 50000, "he_so_co_gian": -0.5,
        },
    }
    r1 = client.post("/api/v1/ops/twin/simulate", json=payload, headers=ql)
    r2 = client.post("/api/v1/ops/twin/simulate", json=payload, headers=ql)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["scenario"]["ket_qua"] == r2.json()["scenario"]["ket_qua"]


def test_twin_virtual_staff_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/ops/twin/virtual-staff",
        json={
            "simulation_id": "sim_test_1",
            "kich_ban": "2 người ca tối",
            "staff_rows": [
                {"id": "nv_01", "ten": "Minh", "loai": "pha_che"},
                {"id": "nv_02", "ten": "Lan", "loai": "phuc_vu"},
            ],
        },
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert "simulation" in body
    assert len(body["simulation"]["staff"]) == 2