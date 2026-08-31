from __future__ import annotations

from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_khung_gio_in_lich_tuan() -> None:
    r = client.get("/api/v1/lich-tuan", headers=headers(client, "lan"))
    assert r.status_code == 200
    body = r.json()
    assert "khung_gio" in body
    assert body["khung_gio"]["sang"]["bat_dau"] == "07:00"
    first = body["ca"][0]
    assert "bat_dau" in first and "ket_thuc" in first


def test_patch_khung_gio_requires_auth() -> None:
    r = client.patch(
        "/api/v1/lich-tuan/khung-gio",
        json={"sang": {"bat_dau": "06:00", "ket_thuc": "11:00"}},
    )
    assert r.status_code == 403


def test_patch_khung_gio_nhanvien_forbidden() -> None:
    r = client.patch(
        "/api/v1/lich-tuan/khung-gio",
        json={"sang": {"bat_dau": "06:00", "ket_thuc": "11:00"}},
        headers=headers(client, "minh"),
    )
    assert r.status_code == 403


def test_patch_khung_gio_quanly_ok() -> None:
    r = client.patch(
        "/api/v1/lich-tuan/khung-gio",
        json={"sang": {"bat_dau": "06:00", "ket_thuc": "11:00"}},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["khung_gio"]["sang"]["bat_dau"] == "06:00"
    assert body["khung_gio"]["sang"]["ket_thuc"] == "11:00"

    r2 = client.get("/api/v1/lich-tuan", headers=headers(client, "lan"))
    sang_ca = [c for c in r2.json()["ca"] if c.get("khung") == "sang"][0]
    assert sang_ca["bat_dau"] == "06:00"
    assert sang_ca["ket_thuc"] == "11:00"


def test_patch_khung_gio_invalid_range() -> None:
    r = client.patch(
        "/api/v1/lich-tuan/khung-gio",
        json={"sang": {"bat_dau": "18:00", "ket_thuc": "06:00"}},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 422
