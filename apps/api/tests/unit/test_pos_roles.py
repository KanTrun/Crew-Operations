from __future__ import annotations

from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_chu_quan_alone_can_manage_menu_and_people() -> None:
    ql = headers(client, "lan")
    chu = headers(client, "hung")

    assert client.get("/api/v1/nguoi", headers=ql).status_code == 403
    people = client.get("/api/v1/nguoi", headers=chu)
    assert people.status_code == 200
    assert {x["username"] for x in people.json()["items"]} >= {"lan", "minh", "hung"}

    forbidden = client.put(
        "/api/v1/menu/tra_chanh",
        json={"ten": "Trà chanh", "gia": 20000, "bom": {"ly": 1}},
        headers=ql,
    )
    assert forbidden.status_code == 403
    saved = client.put(
        "/api/v1/menu/tra_chanh",
        json={"ten": "Trà chanh", "gia": 20000, "bom": {"ly": 1}},
        headers=chu,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["nguon"] == "quan"

    registered = client.post(
        "/api/v1/auth/register",
        json={"username": "hoa", "password": "matkhau01", "display_name": "Hoa"},
    )
    assert registered.status_code == 201
    promoted = client.post("/api/v1/nguoi/hoa/nang-vai", json={}, headers=chu)
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "quan_ly"


def test_pos_requires_checkin_and_staff_only_sees_own_orders() -> None:
    minh = headers(client, "minh")
    hung = headers(client, "hung")
    body = {"dong": [{"mon_id": "mon_sua", "so_luong": 2}], "thanh_toan": "chua_thu"}

    assert client.post("/api/v1/quay/don", json=body, headers=minh).status_code == 403
    assert client.post("/api/v1/diem-danh", headers=minh).status_code == 200
    mine = client.post("/api/v1/quay/don", json=body, headers=minh)
    assert mine.status_code == 201, mine.text
    assert mine.json()["trang_thai"] == "cho_pha"

    assert client.post("/api/v1/diem-danh", headers=hung).status_code == 200
    other = client.post("/api/v1/quay/don", json=body, headers=hung)
    assert other.status_code == 201

    listed = client.get("/api/v1/quay/don", headers=minh)
    assert listed.status_code == 200
    assert [x["id"] for x in listed.json()["items"]] == [mine.json()["id"]]
    assert client.post(
        f"/api/v1/quay/don/{other.json()['id']}/chuyen",
        json={"trang_thai": "dang_pha"},
        headers=minh,
    ).status_code == 403


def test_complete_order_records_estimated_consumption_and_manager_can_fix_active_order() -> None:
    minh = headers(client, "minh")
    lan = headers(client, "lan")
    assert client.post("/api/v1/diem-danh", headers=minh).status_code == 200
    created = client.post(
        "/api/v1/quay/don",
        json={"dong": [{"mon_id": "mon_sua", "so_luong": 2}], "thanh_toan": "chua_thu"},
        headers=minh,
    )
    assert created.status_code == 201, created.text
    don_id = created.json()["id"]

    assert client.post("/api/v1/diem-danh", headers=lan).status_code == 200
    fixed = client.post(
        f"/api/v1/quay/don/{don_id}/chinh",
        json={"dong": [{"mon_id": "mon_sua", "so_luong": 3}], "thanh_toan": "da_ck"},
        headers=lan,
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["dong"][0]["so_luong"] == 3

    assert client.post(
        f"/api/v1/quay/don/{don_id}/chuyen", json={"trang_thai": "dang_pha"}, headers=minh
    ).status_code == 200
    done = client.post(
        f"/api/v1/quay/don/{don_id}/chuyen", json={"trang_thai": "xong"}, headers=minh
    )
    assert done.status_code == 200, done.text
    assert client.post(
        f"/api/v1/quay/don/{don_id}/chuyen", json={"trang_thai": "xong"}, headers=minh
    ).status_code == 409

    consumption = client.get("/api/v1/tieu-thu", headers=minh).json()["items"]
    from_order = [x for x in consumption if x.get("don_quay_id") == don_id]
    assert {x["hang"] for x in from_order} == {"cafe_g", "sua_ml", "ly"}
    assert all(x["nguon"] == "uoc_luong_tu_quay" for x in from_order)

    report = client.get("/api/v1/quay/bao-cao", headers=lan)
    assert report.status_code == 200
    assert report.json()["tong_ly"] == 3
