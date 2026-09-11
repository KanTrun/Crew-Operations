from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_contracts() -> None:
    bad = client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
    assert bad.status_code == 401
    ok = client.post("/api/v1/auth/login", json={"username": "lan", "password": "nhipquan"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "quan_ly"
    assert ok.json()["store_id"] == "quan_01"
    c = client.get("/api/v1/contracts")
    assert c.status_code == 200
    body = c.json()
    assert body["nguon"] == "quan"
    for key in ("NhanVien", "Ca", "LichTuan", "PhieuMau", "RangBuocTrichXuat"):
        assert key in body


def test_lich_tuan_anonymous_forbidden() -> None:
    """Lịch tuần không còn public — yêu cầu quan_ly trở lên."""
    r = client.get("/api/v1/lich-tuan")
    assert r.status_code == 403


def test_lich_tuan_nhanvien_forbidden() -> None:
    """Nhân viên không được đọc lịch tuần qua API — chỉ xem qua UI hôm nay của mình."""
    r = client.get("/api/v1/lich-tuan", headers=headers(client, "minh"))
    assert r.status_code == 403


def test_lich_tuan_quanly_ok() -> None:
    r = client.get("/api/v1/lich-tuan", headers=headers(client, "lan"))
    assert r.status_code == 200
    body = r.json()
    assert body["nguon"] == "quan"
    assert "phan_cong" in body
    assert "ca" in body
    assert "nhan_vien" in body


def test_lich_tuan_with_tuan_param() -> None:
    r = client.get("/api/v1/lich-tuan?tuan=2026-W36", headers=headers(client, "lan"))
    assert r.status_code == 200
    body = r.json()
    assert body.get("tuan_iso") == "2026-W36"


def test_pin_requires_auth() -> None:
    r = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "ca_01", "nv_id": "nv_01", "pinned": True},
    )
    assert r.status_code == 403


def test_pin_nhanvien_forbidden() -> None:
    r = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "ca_01", "nv_id": "nv_01", "pinned": True},
        headers=headers(client, "minh"),
    )
    assert r.status_code == 403


def test_pin_quanly_ok() -> None:
    r = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c01", "nv_id": "nv_01", "pinned": True},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200
    assert r.json()["pinned"] is True


def test_pin_unknown_ids_404() -> None:
    r = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "ca_nope", "nv_id": "nv_01", "pinned": True},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 404


def test_pin_rejects_missing_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ghim NV thiếu kỹ năng vị trí ca → 422, không để solver INFEASIBLE âm thầm.

    NV seed nv_06 (Chi Vũ) chỉ biết thu_ngan; w1_c01 là role-slot pha_che.
    Bật seed pool qua env để nv_06 vào pool xếp lịch (users thật luôn đủ kỹ năng).
    """
    from ca_api.persist import kv_get

    monkeypatch.setenv("NHIPQUAN_LOI_GIAI_SEED", "1")
    lan = headers(client, "lan")
    r = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c01", "nv_id": "nv_06", "pinned": True},
        headers=lan,
    )
    assert r.status_code == 422, r.text
    assert "nv_thieu_ky_nang" in r.json()["detail"]
    assert kv_get("pins", {}).get("w1_c01|nv_06") is None

    # Cùng NV pin vào role-slot khớp kỹ năng (w1_c05 thu_ngan) thì vẫn thành công.
    r_ok = client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c05", "nv_id": "nv_06", "pinned": True},
        headers=lan,
    )
    assert r_ok.status_code == 200, r_ok.text


def test_pin_reflected_in_lich_tuan() -> None:
    """Pin NV thật rồi đọc lại — hành vi sau khi pool = users (seed tắt mặc định)."""
    from ca_api.persist import list_users

    nv_that = next(u["nv_id"] for u in list_users() if u["role"] == "nhan_vien")
    client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c02", "nv_id": nv_that, "pinned": True},
        headers=headers(client, "lan"),
    )
    r = client.get("/api/v1/lich-tuan", headers=headers(client, "lan"))
    body = r.json()
    phan_cong = body["phan_cong"]
    assert nv_that in phan_cong.get("w1_c02", []), f"pin {nv_that} phải hiện trong w1_c02"


def test_lifecycle_quanly_can_set() -> None:
    # Đi đúng chuỗi: may_sinh → nhap → dang_giai (solver chạy, tự sang cho_duyet).
    ql = headers(client, "lan")
    r0 = client.patch(
        "/api/v1/lich-tuan/lifecycle",
        json={"trang_thai": "nhap", "tuan_iso": "2026-W36"},
        headers=ql,
    )
    assert r0.status_code == 200, r0.text
    r1 = client.patch(
        "/api/v1/lich-tuan/lifecycle",
        json={"trang_thai": "dang_giai"},
        headers=ql,
    )
    assert r1.status_code == 200, r1.text
    # dang_giai chạy solver xong tự chuyển cho_duyet — PATCH trả trạng thái mới.
    body = r1.json()
    assert body["ok"] is True
    assert body["trang_thai"] == "cho_duyet"


def test_lifecycle_rejects_illegal_jump() -> None:
    """PATCH không cho nhảy tắt — may_sinh chỉ sang nhap, không thẳng cho_duyet."""
    r = client.patch(
        "/api/v1/lich-tuan/lifecycle",
        json={"trang_thai": "cho_duyet"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 409
    assert "illegal:" in r.json()["detail"]


def test_lifecycle_invalid_state() -> None:
    r = client.patch(
        "/api/v1/lich-tuan/lifecycle",
        json={"trang_thai": "khong_ton_tai"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 422


def test_lifecycle_nhanvien_forbidden() -> None:
    r = client.patch(
        "/api/v1/lich-tuan/lifecycle",
        json={"trang_thai": "cho_duyet"},
        headers=headers(client, "minh"),
    )
    assert r.status_code == 403

