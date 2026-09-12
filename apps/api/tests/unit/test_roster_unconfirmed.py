from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get, kv_set
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_get_lich_tuan_unconfirmed_detection() -> None:
    # Reset decisions
    kv_set("roster_nv_status", {})
    r = client.get("/api/v1/lich-tuan?tuan=2026-W36", headers=headers(client, "lan"))
    assert r.status_code == 200
    body = r.json()

    assert "chua_xac_nhan" in body
    assert "du_bi" in body
    assert "nv_status_map" in body

    # Staff who have assigned shifts but haven't submitted constraints should be in chua_xac_nhan
    chua_xac_nhan = body["chua_xac_nhan"]
    assert isinstance(chua_xac_nhan, list)
    if chua_xac_nhan:
        first = chua_xac_nhan[0]
        assert "id" in first
        assert "ten" in first
        assert "so_ca_du_kien" in first
        assert first["so_ca_du_kien"] > 0


def test_post_nv_status_xac_nhan() -> None:
    tuan = "2026-W36"
    kv_set("roster_nv_status", {})
    r = client.get(f"/api/v1/lich-tuan?tuan={tuan}", headers=headers(client, "lan"))
    body = r.json()
    if not body.get("chua_xac_nhan"):
        # Put an assignment
        kv_set("phan_cong", {"1": ["nv_03"]})
        r = client.get(f"/api/v1/lich-tuan?tuan={tuan}", headers=headers(client, "lan"))
        body = r.json()

    target_nv = body["chua_xac_nhan"][0]["id"]

    # Manager confirms shifts
    res = client.post(
        "/api/v1/lich-tuan/nv-status",
        json={"tuan_iso": tuan, "nv_id": target_nv, "hanh_dong": "xac_nhan"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    # Check updated roster
    r2 = client.get(f"/api/v1/lich-tuan?tuan={tuan}", headers=headers(client, "lan"))
    body2 = r2.json()
    chua_xac_nhan_ids = [x["id"] for x in body2["chua_xac_nhan"]]
    assert target_nv not in chua_xac_nhan_ids
    assert body2["nv_status_map"].get(target_nv) == "xac_nhan"


def test_post_nv_status_du_bi() -> None:
    tuan = "2026-W36"
    # Ensure nv_03 is assigned to shift 1
    kv_set("phan_cong", {"1": ["nv_03", "nv_01"], "2": ["nv_03"]})
    kv_set("roster_nv_status", {})

    # Manager moves nv_03 to on-call (du_bi)
    res = client.post(
        "/api/v1/lich-tuan/nv-status",
        json={"tuan_iso": tuan, "nv_id": "nv_03", "hanh_dong": "du_bi"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200

    r = client.get(f"/api/v1/lich-tuan?tuan={tuan}", headers=headers(client, "lan"))
    body = r.json()
    du_bi_ids = [x["id"] for x in body["du_bi"]]
    assert "nv_03" in du_bi_ids
    assert body["nv_status_map"].get("nv_03") == "du_bi"

    # nv_03 should be removed from all shifts in phan_cong
    for _ca_id, nv_ids in body["phan_cong"].items():
        assert "nv_03" not in nv_ids


def test_post_nv_status_bo_ca() -> None:
    tuan = "2026-W36"
    kv_set("phan_cong", {"1": ["nv_02"], "2": ["nv_02", "nv_01"]})
    kv_set("roster_nv_status", {})

    res = client.post(
        "/api/v1/lich-tuan/nv-status",
        json={"tuan_iso": tuan, "nv_id": "nv_02", "hanh_dong": "bo_ca"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200

    r = client.get(f"/api/v1/lich-tuan?tuan={tuan}", headers=headers(client, "lan"))
    body = r.json()
    for _ca_id, nv_ids in body["phan_cong"].items():
        assert "nv_02" not in nv_ids
    assert body["nv_status_map"].get("nv_02") == "bo_ca"


def test_post_nv_status_forbidden_for_nhanvien() -> None:
    tuan = "2026-W36"
    res = client.post(
        "/api/v1/lich-tuan/nv-status",
        json={"tuan_iso": tuan, "nv_id": "nv_03", "hanh_dong": "xac_nhan"},
        headers=headers(client, "minh"),
    )
    assert res.status_code == 403


def test_post_nv_self_confirm() -> None:
    tuan = "2026-W36"
    kv_set("roster_nv_status", {})
    # Minh (nhan_vien) logs in and confirms their own availability
    res = client.post(
        "/api/v1/lich-tuan/xac-nhan-lich",
        json={"tuan_iso": tuan},
        headers=headers(client, "minh"),
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    # Check that status store now has minh's nv_id confirmed
    status_store = kv_get("roster_nv_status", {})
    assert status_store.get(tuan, {}).get("nv_03") == "xac_nhan"
