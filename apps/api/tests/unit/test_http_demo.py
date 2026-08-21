from __future__ import annotations

from fastapi.testclient import TestClient

from ca_api.interfaces.http.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_contracts() -> None:
    bad = client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
    assert bad.status_code == 401
    ok = client.post("/api/v1/auth/login", json={"username": "quanly", "password": "demo"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "quan_ly"
    c = client.get("/api/v1/contracts")
    assert c.status_code == 200
    body = c.json()
    assert body["nguon"] == "fixture_synthetic"
    for key in ("NhanVien", "Ca", "LichTuan", "PhieuMau", "RangBuocTrichXuat"):
        assert key in body
