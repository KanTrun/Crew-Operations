"""Pin nhận users thật + lịch chưa xếp trả khung trống (hết mock roster)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from ca_api.persist import kv_set, register
from fastapi.testclient import TestClient

client = TestClient(app)


def _login_manager() -> str:
    res = client.post("/api/v1/auth/login", json={"username": "lan", "password": "nhipquan"})
    assert res.status_code == 200
    return res.json()["token"]


def test_pin_nhan_nv_that() -> None:
    """Pin NV đăng ký thật (nv_26+) phải thành công — trước đây chỉ seed được."""
    new = register("pin_test_nv", "matkhautot123", "Pin Test NV")
    nv_id = new["nv_id"]
    token = _login_manager()
    res = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c01", "nv_id": nv_id, "pinned": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True
    # Gỡ lại cho sạch
    res2 = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c01", "nv_id": nv_id, "pinned": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200


def test_pin_tu_choi_id_la() -> None:
    """NV id không tồn tại → 404 (fail-closed giữ nguyên)."""
    token = _login_manager()
    res = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c01", "nv_id": "nv_khong_ton_tai_99", "pinned": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def test_lich_chua_xep_tra_khung_trong(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Chưa chạy solver và chưa seed phân công: roster vẫn chỉ có khung ca."""
    import ca_api.interfaces.http.main as m

    monkeypatch.setattr(m, "LICH_TUAN_OUT", tmp_path / "khong_co_lich.json")
    kv_set("phan_cong", {})
    token = _login_manager()
    res = client.get("/api/v1/lich-tuan", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["nguon_lich"] == "chua_xep"
    # Không còn phân công giả từ pattern seed
    assert data["phan_cong"] == {}
    # Ca mẫu vẫn đủ để UI vẽ lưới
    assert len(data["ca"]) >= 20


def test_lich_tra_phan_cong_da_seed_khi_chua_co_solver(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Seed demo phải hiện trên roster ngay cả trước khi solver tạo output file."""
    import ca_api.interfaces.http.main as m

    monkeypatch.setattr(m, "LICH_TUAN_OUT", tmp_path / "khong_co_lich.json")
    kv_set("phan_cong", {"w1_c01": ["nv_01", "nv_02"]})
    token = _login_manager()
    res = client.get("/api/v1/lich-tuan", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["phan_cong"]["w1_c01"] == ["nv_01", "nv_02"]


def test_lich_solver_partial_khong_lam_mat_phan_cong_seed(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Solver output thiếu ca không được xóa phân công seed còn lại."""
    import ca_api.interfaces.http.main as m

    output = tmp_path / "lich_tuan.json"
    output.write_text(
        '{"ok": true, "status": "optimal", "phan_cong": {"w1_c01": ["nv_03"]}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(m, "LICH_TUAN_OUT", output)
    kv_set("phan_cong", {"w1_c01": ["nv_01"], "w1_c02": ["nv_02", "nv_03"]})
    token = _login_manager()
    res = client.get("/api/v1/lich-tuan", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assignments = res.json()["phan_cong"]
    assert assignments["w1_c01"] == ["nv_03"]
    assert assignments["w1_c02"] == ["nv_02", "nv_03"]


def test_lich_output_rong_fallback_phan_cong_seed_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Output solver rỗng không được che mất lịch seed đã có trong fixture."""
    import ca_api.interfaces.http.main as m

    output = tmp_path / "lich_tuan.json"
    output.write_text('{"ok": true, "status": "optimal", "phan_cong": {}}', encoding="utf-8")
    monkeypatch.setattr(m, "LICH_TUAN_OUT", output)
    kv_set("phan_cong", {})
    token = _login_manager()
    res = client.get(
        "/api/v1/lich-tuan?tuan=2026-W01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assignments = res.json()["phan_cong"]
    # w1_c01 là role-slot pha_che cần 2 người — lịch sử tuần 1 phải có đủ 2.
    w1_c01 = assignments.get("w1_c01", [])
    assert len(w1_c01) == 2, f"w1_c01 phải có 2 pha chế, got {w1_c01}"
