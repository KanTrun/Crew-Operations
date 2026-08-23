from __future__ import annotations

from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)
PHOTO = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="


def test_phieu_twenty_steps_and_treo() -> None:
    auth = headers(client, "minh")
    client.post("/api/v1/diem-danh", headers=auth)
    r = client.post("/api/v1/phieu/start", json={"mau": "mo_quan"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["so_buoc"] >= 20
    pid = body["id"]
    for b in body["buocs"]:
        if b["loai"] == "photo":
            rr = client.post(
                f"/api/v1/phieu/{pid}/minh-chung",
                json={"buoc_ma": b["ma"], "data_url": PHOTO},
                headers=auth,
            )
        else:
            rr = client.post(
                f"/api/v1/phieu/{pid}/buoc",
                json={"ma": b["ma"], "gia_tri": "4" if b["loai"] == "text" else "ok"},
                headers=auth,
            )
        assert rr.status_code == 200, rr.text
        body = rr.json()
    assert body["trang_thai"] == "hoan_thanh"
    timing = body["signals"]["timing_ms"]
    assert isinstance(timing, dict)
    assert timing
    assert all(isinstance(k, str) for k in timing)
    tr = client.post(
        f"/api/v1/phieu/{pid}/treo",
        json={"noi_dung": "hết đá"},
        headers=auth,
    )
    assert tr.status_code == 200
    hung = client.get("/api/v1/viec-treo", headers=auth).json()["items"]
    assert any("đá" in x["noi_dung"] for x in hung)


def test_photo_rejected_without_payload() -> None:
    auth = headers(client, "minh")
    client.post("/api/v1/diem-danh", headers=auth)
    r = client.post("/api/v1/phieu/start", json={"mau": "mo_quan"}, headers=auth)
    pid = r.json()["id"]
    first_photo = next(b for b in r.json()["buocs"] if b["loai"] == "photo")
    for b in r.json()["buocs"]:
        if b["ma"] == first_photo["ma"]:
            break
        client.post(
            f"/api/v1/phieu/{pid}/buoc",
            json={"ma": b["ma"], "gia_tri": "4"},
            headers=auth,
        )
    bad = client.post(
        f"/api/v1/phieu/{pid}/minh-chung",
        json={"buoc_ma": first_photo["ma"], "data_url": ""},
        headers=auth,
    )
    assert bad.status_code == 400


def test_start_requires_diem_danh() -> None:
    chu = headers(client, "hung")
    r = client.post("/api/v1/phieu/start", json={"mau": "mo_quan"}, headers=chu)
    assert r.status_code == 403


def test_orc_idempotency() -> None:
    ql = headers(client, "lan")
    a = client.post("/api/v1/orc/dispatch", json={"n": 8, "key": "k-test"}, headers=ql).json()
    b = client.post("/api/v1/orc/dispatch", json={"n": 8, "key": "k-test"}, headers=ql).json()
    assert a["n"] == 8
    assert a["writes"] == 8
    assert a["replayed"] is False
    assert b["replayed"] is True
    assert b["writes"] == 8


def test_ghi_nhan_after_nha() -> None:
    auth = headers(client, "minh")
    nhan = client.post("/api/v1/ca/nhan", json={"ca_id": "w1_c01"}, headers=auth)
    assert nhan.status_code == 200, nhan.text
    assert nhan.json()["truoc"] != nhan.json()["sau"]
    nha = client.post("/api/v1/ca/nha", json={"ca_id": "w1_c01"}, headers=auth)
    assert nha.status_code == 200, nha.text
    assert "nv_03" in nha.json()["truoc"]
    assert "nv_03" not in nha.json()["sau"]
    items = client.get("/api/v1/ghi-nhan-sua", headers=auth).json()["items"]
    assert items
    last = items[-1]
    assert "truoc" in last and "sau" in last
    assert last["truoc"] != last["sau"]


def test_phieu_seq_unique_under_parallel() -> None:
    from concurrent.futures import ThreadPoolExecutor

    auth = headers(client, "minh")
    client.post("/api/v1/diem-danh", headers=auth)

    def start() -> str:
        r = client.post("/api/v1/phieu/start", json={"mau": "mo_quan"}, headers=auth)
        assert r.status_code == 200, r.text
        return r.json()["id"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: start(), range(8)))
    assert len(ids) == len(set(ids))
