from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_playbook import record_sua
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def _seed_three_sua() -> None:
    for i in range(3):
        record_sua(
            loai="nhan_ca",
            truoc={"ca_id": "w1_c10", "nv": []},
            sau={"ca_id": "w1_c10", "nv": [f"nv_{i+10:02d}"]},
            ai="lan",
            now_iso=f"2026-01-0{i+1}T08:00:00Z",
        )


def test_lifecycle_and_audit() -> None:
    ql = headers(client, "lan")
    r = client.post("/api/v1/lich/lifecycle", json={"to": "dang_giai"}, headers=ql)
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "dang_giai"
    client.post("/api/v1/lich/lifecycle", json={"to": "cho_duyet"}, headers=ql)
    client.post("/api/v1/lich/lifecycle", json={"to": "da_cong_bo"}, headers=ql)
    ics = client.get("/api/v1/lich/ics", headers=ql).json()
    assert "BEGIN:VCALENDAR" in ics["ics"]
    log = client.get("/api/v1/audit", headers=ql).json()["items"]
    assert log


def test_inbox_ten_decisions() -> None:
    ql = headers(client, "lan")
    items = client.get("/api/v1/inbox/rang-buoc", headers=ql).json()["items"]
    assert len(items) >= 10
    for it in items[:10]:
        d = "duyet" if it["id"].endswith(("1", "2", "3", "4", "5")) else "tu_choi"
        rr = client.post(
            f"/api/v1/inbox/rang-buoc/{it['id']}",
            json={"quyet_dinh": d},
            headers=ql,
        )
        assert rr.status_code == 200, rr.text


def test_inbox_msg_does_not_break_rang_buoc() -> None:
    ql = headers(client, "lan")
    client.post("/api/v1/inbox", json={"tom_tat": "tin nhắn"}, headers=ql)
    items = client.get("/api/v1/inbox/rang-buoc", headers=ql).json()["items"]
    assert len(items) >= 10
    assert all("id" in it for it in items)


def test_conflict_never_picks() -> None:
    body = client.get("/api/v1/vf/conflict").json()
    assert body["conflict"] is True
    assert body["khong_tu_chon"] is True


def test_handover_sbar() -> None:
    nv = headers(client, "minh")
    text = (
        "Tình hình: hết đá\nBối cảnh: ca sáng\n"
        "Đánh giá: khách đông\nĐề nghị: mua đá\nTreo: máy pha kêu"
    )
    r = client.post("/api/v1/handover", json={"text": text, "alt_claim": "ổn"}, headers=nv)
    assert r.status_code == 200
    assert "hết đá" in r.json()["tinh_hinh"]


def test_cam_nang_eight_steps_and_vf_rule_reject() -> None:
    _seed_three_sua()
    ql = headers(client, "lan")
    r = client.post("/api/v1/cam-nang/chay-8-buoc", headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["hieu_luc"]["trang_thai"] == "hieu_luc"
    assert body["hieu_luc"]["buoc"] == 8
    assert body["bi_loai"]["trang_thai"] == "loai"
    assert body["tu_tat_60pct"]["trang_thai"] == "tu_tat"
    assert body["so_luat_that_quan"] == 0
    cards = client.get("/api/v1/cam-nang", headers=ql).json()["items"]
    assert any(x.get("trang_thai") == "hieu_luc" for x in cards)


def test_cam_nang_requires_real_edits() -> None:
    ql = headers(client, "lan")
    r = client.post("/api/v1/cam-nang/chay-8-buoc", headers=ql)
    assert r.status_code == 409


def test_sop_twenty_with_citation_or_unknown() -> None:
    ql = headers(client, "lan")
    r = client.get("/api/v1/sop/golden", headers=ql).json()
    assert r["n"] == 20
    assert r["moi_cau_co_nguon_hoac_chua_co"] is True
    assert r["co_cau_chua_co"] is True


def test_qr_one_shot() -> None:
    ql = headers(client, "lan")
    nv = headers(client, "minh")
    tok = client.post("/api/v1/qr", json={"nv_id": "nv_03"}, headers=ql).json()["token"]
    assert client.post(f"/api/v1/qr/{tok}", headers=nv).status_code == 200
    assert client.post(f"/api/v1/qr/{tok}", headers=nv).status_code == 409


def test_swap_three_way() -> None:
    nv = headers(client, "minh")
    r = client.post(
        "/api/v1/cho-doi-ca",
        json={"a": "nv_03", "b": "nv_04", "c": "nv_05", "ca_id": "w1_c01"},
        headers=nv,
    )
    assert r.status_code == 200
    assert r.json()["trang_thai"] == "cho_3_nhanh"


def test_fairness_scoped_to_self_for_nv() -> None:
    nv = headers(client, "minh")
    r = client.get("/api/v1/cong-bang", headers=nv).json()
    assert r["khong_xep_hang_ten"] is True
    assert "cuoi_tuan" in r["axes"]
    assert set(r["so_du"].keys()) == {"nv_03"}
    assert r["nv_id"] == "nv_03"
