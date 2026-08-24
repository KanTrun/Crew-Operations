from __future__ import annotations

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
    c = client.get("/api/v1/contracts")
    assert c.status_code == 200
    body = c.json()
    assert body["nguon"] == "quan"
    for key in ("NhanVien", "Ca", "LichTuan", "PhieuMau", "RangBuocTrichXuat"):
        assert key in body


def test_lich_tuan_anonymous_read() -> None:
    r = client.get("/api/v1/lich-tuan")
    assert r.status_code == 200
    body = r.json()
    assert body["nguon"] == "quan"
    assert "phan_cong" in body
    assert "ca" in body
    assert "nhan_vien" in body


def test_lich_tuan_with_tuan_param() -> None:
    r = client.get("/api/v1/lich-tuan?tuan=2026-W34")
    assert r.status_code == 200
    body = r.json()
    assert body.get("tuan_iso") == "2026-W34"


def test_lich_tuan_nhanvien_read_only() -> None:
    r = client.get("/api/v1/lich-tuan", headers=headers(client, "minh"))
    assert r.status_code == 200


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


def test_pin_reflected_in_lich_tuan() -> None:
    client.post(
        "/api/v1/lich-tuan/pin",
        json={"ca_id": "w1_c02", "nv_id": "nv_05", "pinned": True},
        headers=headers(client, "lan"),
    )
    r = client.get("/api/v1/lich-tuan")
    body = r.json()
    phan_cong = body["phan_cong"]
    assert "nv_05" in phan_cong.get("w1_c02", [])


def test_register_creates_staff_session() -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": "minh_pha_che",
            "password": "caphe12345",
            "display_name": "Minh pha chế",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "nhan_vien"
    assert body["token"]
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "minh_pha_che"


def test_register_rejects_duplicate_and_invalid() -> None:
    payload = {
        "username": "lan",
        "password": "caphe12345",
        "display_name": "Ai đó",
    }
    dup = client.post("/api/v1/auth/register", json=payload)
    assert dup.status_code == 409
    assert dup.json()["detail"] == "ten_da_ton_tai"

    bad = client.post(
        "/api/v1/auth/register",
        json={"username": "A B", "password": "123", "display_name": "x"},
    )
    assert bad.status_code == 409
    assert bad.json()["detail"] in {
        "ten_khong_hop_le",
        "mat_khau_qua_ngan",
        "thieu_ten_hien_thi",
    }
