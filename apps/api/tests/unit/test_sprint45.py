from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from ca_agents.ag_rule import RuleDraft
from ca_api.interfaces.http import sprint45
from ca_api.interfaces.http.main import app
from ca_api.persist import da_diem_danh, kv_get, kv_set
from ca_playbook import record_sua
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def _hom_nay() -> str:
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()


def _seed_three_sua() -> None:
    for i in range(3):
        record_sua(
            loai="nhan_ca",
            truoc={"ca_id": "w1_c10", "nv": []},
            sau={"ca_id": "w1_c10", "nv": [f"nv_{i + 10:02d}"]},
            ai="lan",
            now_iso=f"2026-01-0{i + 1}T08:00:00Z",
        )


def _seed_three_nha_ca() -> None:
    """Ba lần nhả ca — ``sau`` không còn ai nên không suy ra được số người."""
    for i in range(3):
        record_sua(
            loai="nha_ca",
            truoc={"ca_id": "w1_c11", "nv": [f"nv_{i + 10:02d}"]},
            sau={"ca_id": "w1_c11", "nv": []},
            ai="lan",
            now_iso=f"2026-01-0{i + 1}T09:00:00Z",
        )


def test_lifecycle_and_audit() -> None:
    ql = headers(client, "lan")
    chu = headers(client, "hung")
    # Đúng chuỗi: may_sinh → nhap → dang_giai (solver) → cho_duyet → da_cong_bo.
    client.post("/api/v1/lich/lifecycle", json={"to": "nhap"}, headers=ql)
    r = client.post("/api/v1/lich/lifecycle", json={"to": "dang_giai"}, headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trang_thai"] == "dang_giai"
    assert body.get("solver", {}).get("status")
    client.post("/api/v1/lich/lifecycle", json={"to": "cho_duyet"}, headers=ql)
    client.post("/api/v1/lich/lifecycle", json={"to": "da_duyet"}, headers=ql)
    client.post("/api/v1/lich/lifecycle", json={"to": "da_cong_bo"}, headers=ql)
    ics = client.get("/api/v1/lich/ics", headers=ql).json()
    assert "BEGIN:VCALENDAR" in ics["ics"]
    assert client.get("/api/v1/audit", headers=ql).status_code == 403
    log = client.get("/api/v1/audit", headers=chu).json()["items"]
    assert log
    assert log[0]["id"] >= log[-1]["id"]
    assert isinstance(log[0]["payload"], dict)
    assert log[0]["payload"]["to"] in {"dang_giai", "cho_duyet", "da_cong_bo"}


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


def test_cam_nang_eight_steps_den_cho_chu_quan() -> None:
    """Chạy 8 bước trên lần sửa thật: luật suy tất định phải qua VF và chờ chủ quán.

    Không có ``bi_loai`` ở đường này là đúng: suy luật tất định
    (``derive_rule_from_edits``) chỉ sinh câu và ``dieu_kien`` hợp hợp đồng nên
    cổng VF-RULE không có gì để loại. Ví dụ luật bị loại cho demo nằm ở fixture
    ``luat_cam_nang`` (xem test_seed_van_hanh), không do API bịa ra.
    """
    _seed_three_sua()
    ql = headers(client, "lan")
    chu = headers(client, "hung")
    r = client.post("/api/v1/cam-nang/chay-8-buoc", headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cho_chot"]["trang_thai"] == "cho_chu_quan"
    assert body["cho_chot"]["buoc"] == 6
    assert body["cho_chot"]["cau"].strip()
    assert body["bi_loai"] is None
    assert body["so_luat_that_quan"] >= 1
    assert [x["mau"] for x in body["ung_vien"]] == ["nhan_ca"]
    assert client.post(
        "/api/v1/cam-nang/duyet", json={"id": body["cho_chot"]["id"], "ok": True}, headers=ql
    ).status_code == 403
    final = client.post(
        "/api/v1/cam-nang/duyet", json={"id": body["cho_chot"]["id"], "ok": True}, headers=chu
    )
    assert final.status_code == 200, final.text
    assert final.json()["trang_thai"] == "hieu_luc"
    cards = client.get("/api/v1/cam-nang", headers=ql).json()["items"]
    assert any(x.get("trang_thai") == "hieu_luc" for x in cards)


def test_cam_nang_bao_luat_bi_vf_rule_loai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bản nháp của agent vi phạm VF-RULE thì bị loại và được báo ra, không lọt."""
    _seed_three_sua()
    xau = RuleDraft(
        cau="nv_03 lười không xếp cuối tuần",
        loai="ghep_ky_nang",
        dieu_kien={"thu": "T7"},
        bang_chung=["0", "1", "2"],
        do_tin_cay=0.75,
    )
    monkeypatch.setattr(sprint45, "propose_rule", lambda *a, **k: xau)

    ql = headers(client, "lan")
    r = client.post("/api/v1/cam-nang/chay-8-buoc", headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cho_chot"] is None
    assert body["bi_loai"]["trang_thai"] == "loai"
    assert body["bi_loai"]["vf_rule"] == "luat_ve_nguoi"
    assert body["ung_vien"][0]["vf_rule"] == "luat_ve_nguoi"
    cards = client.get("/api/v1/cam-nang", headers=ql).json()["items"]
    assert any(x.get("trang_thai") == "loai" for x in cards)


def test_cam_nang_bao_khong_du_tin_hieu_khi_thieu_tin_hieu() -> None:
    """Ba lần nhả ca làm trống ca: không có tín hiệu số người nên không suy được luật.

    Đường này phải báo ``khong_du_tin_hieu`` chứ không được dựng một câu luật
    bịa để lấp chỗ trống.
    """
    _seed_three_nha_ca()
    ql = headers(client, "lan")
    r = client.post("/api/v1/cam-nang/chay-8-buoc", headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cho_chot"] is None
    assert body["bi_loai"] is None
    assert body["ung_vien"] == [
        {"mau": "nha_ca", "trang_thai": "khong_du_tin_hieu", "buoc": 3, "id": None}
    ]
    assert client.get("/api/v1/cam-nang", headers=ql).json()["items"] == []


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


def test_qr_can_only_be_used_by_target_employee() -> None:
    manager = headers(client, "lan")
    other = headers(client, "hung")
    target = headers(client, "minh")
    token = client.post("/api/v1/qr", json={"nv_id": "nv_03", "ca_id": "w1_c01"}, headers=manager).json()["token"]
    assert client.post(f"/api/v1/qr/{token}", headers=other).status_code == 403
    assert client.post(f"/api/v1/qr/{token}", headers=target).status_code == 200
    assert "nv_03" in kv_get("diem_danh", {}).get(_hom_nay(), [])


def test_qr_diem_danh_chi_hieu_luc_trong_ngay() -> None:
    """Điểm danh scoped theo ngày — ngày khác không tính, phải quét lại."""
    kv_set("diem_danh", {"2000-01-01": ["nv_03"]})
    assert da_diem_danh("nv_03") is False
    # Bản cũ dạng list vẫn đọc được (tương thích ngược)
    kv_set("diem_danh", ["nv_03"])
    assert da_diem_danh("nv_03") is True


def test_qr_write_path_tuong_thich_nguoc_du_lieu_list_cu() -> None:
    """QR check-in ghi cùng KV `diem_danh` — bản cũ dạng list phải migrate, không 500.

    Regression cùng lớp lỗi với /api/v1/diem-danh: `dd_mut()` gọi `.get()` trên
    list → AttributeError → 500, nhân viên không quét QR vào ca được.
    """
    kv_set("diem_danh", ["nv_09"])
    manager = headers(client, "lan")
    target = headers(client, "minh")
    token = client.post("/api/v1/qr", json={"nv_id": "nv_03", "ca_id": "w1_c01"}, headers=manager).json()["token"]

    r = client.post(f"/api/v1/qr/{token}", headers=target)

    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    luu = kv_get("diem_danh", {})
    assert isinstance(luu, dict)
    assert set(luu[_hom_nay()]) == {"nv_09", "nv_03"}


def test_swap_requires_valid_shift_and_staff_participation() -> None:
    staff = headers(client, "minh")
    outsider = {"a": "nv_01", "b": "nv_02", "c": "nv_04", "ca_id": "w1_c01"}
    assert client.post("/api/v1/cho-doi-ca", json=outsider, headers=staff).status_code == 403
    invalid = {"a": "nv_03", "b": "nv_04", "c": "nv_05", "ca_id": "missing"}
    assert client.post("/api/v1/cho-doi-ca", json=invalid, headers=staff).status_code == 422


def test_ops_pickers_for_staff() -> None:
    nv = headers(client, "minh")
    r = client.get("/api/v1/ops/pickers", headers=nv)
    assert r.status_code == 200
    body = r.json()
    assert {person["id"] for person in body["nhan_vien"]} >= {"nv_01", "nv_02", "nv_03"}
    assert "nv_04" not in {person["id"] for person in body["nhan_vien"]}
    assert len(body["ca"]) >= 3
    assert body["me_nv_id"] == "nv_03"


def test_swap_consent_three_branches() -> None:
    opened = client.post(
        "/api/v1/cho-doi-ca",
        json={"a": "nv_03", "b": "nv_02", "c": "nv_01", "ca_id": "w1_c01"},
        headers=headers(client, "minh"),
    ).json()
    swap_id = opened["id"]
    client.post(f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "minh"))
    client.post(f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "hung"))
    done = client.post(f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "lan")).json()
    assert done["trang_thai"] == "dong_y"
    assert len(done.get("dong_y", [])) == 3


def test_swap_tu_choi_idor_protection() -> None:
    # Đăng ký một nhân viên mới không liên quan đến ca đổi
    reg = client.post(
        "/api/v1/auth/register",
        json={"username": "nv_ngoai_cuoc", "password": "password123", "display_name": "Người Ngoài Cuộc"},
    ).json()
    headers_outsider = {"Authorization": f"Bearer {reg['token']}"}

    opened = client.post(
        "/api/v1/cho-doi-ca",
        json={"a": "nv_03", "b": "nv_02", "c": "nv_01", "ca_id": "w1_c01"},
        headers=headers(client, "minh"),
    ).json()
    swap_id = opened["id"]

    # Nhân viên ngoài cuộc không có quyền từ chối yêu cầu đổi ca của người khác
    res_reject = client.post(f"/api/v1/cho-doi-ca/{swap_id}/tu-choi", headers=headers_outsider)
    assert res_reject.status_code == 403
    assert res_reject.json()["detail"] == "khong_phai_nguoi_tham_gia"

    # Người trong cuộc (Minh - nv_03) có quyền từ chối
    res_ok = client.post(f"/api/v1/cho-doi-ca/{swap_id}/tu-choi", headers=headers(client, "minh"))
    assert res_ok.status_code == 200
    assert res_ok.json()["trang_thai"] == "tu_choi"


def test_lich_ics_event_fields_rfc5545() -> None:
    ql = headers(client, "lan")
    from ca_api.persist import kv_mutate
    kv_mutate("phan_cong", lambda _: {"w1_c01": ["nv_01", "nv_02"]}, {})
    ics = client.get("/api/v1/lich/ics", headers=ql).json()
    assert "BEGIN:VCALENDAR" in ics["ics"]
    assert "BEGIN:VEVENT" in ics["ics"]
    assert "DTSTART:" in ics["ics"]
    assert "DTEND:" in ics["ics"]
    assert "DTSTAMP:" in ics["ics"]
    assert "END:VEVENT" in ics["ics"]



def test_hom_nay_preview_fields() -> None:
    ql = headers(client, "lan")
    body = client.get("/api/v1/hom-nay", headers=ql).json()
    assert "treo_preview" in body
    assert "treo_theo_trang_thai" in body
    assert "sua_gan_day" in body
    assert "ton_tom_tat" in body


def test_handover_history_list() -> None:
    nv = headers(client, "minh")
    client.post(
        "/api/v1/handover",
        json={"text": "Tình hình: test\nBối cảnh: a\nĐánh giá: b\nĐề nghị: c"},
        headers=nv,
    )
    items = client.get("/api/v1/handover", headers=nv).json()["items"]
    assert len(items) >= 1
