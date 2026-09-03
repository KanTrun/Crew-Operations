"""Unit & Integration tests for Meeting API endpoints."""

from __future__ import annotations

import base64

import pytest
from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _pin_replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    # Neo replay mode: test khác trong full suite có thể set CA_AGENT_MODE=live
    # (qua ensure_dotenv) và leak env sang đây — phải cô lập để assert ổn định.
    monkeypatch.setenv("CA_AGENT_MODE", "replay")


def test_meeting_transcribe_endpoint() -> None:
    ql = headers(client, "lan")
    fake_b64 = base64.b64encode(b"dummy_meeting_audio").decode("ascii")
    
    res = client.post(
        "/api/v1/meeting/transcribe",
        json={"audio_base64": fake_b64, "mime_type": "audio/webm"},
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert len(body["segments"]) >= 1


def test_meeting_analyze_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/meeting/analyze",
        json={
            "text": "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h. My đổi định lượng trà đào sang 20ml.",
            "meeting_type": "giao_ca",
            "audio_source": "google_meet_tab",
        },
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["loai_hop"] == "giao_ca"
    assert len(body["action_items"]) >= 1
    assert body["trang_thai"] == "cho_duyet"


def test_meeting_apply_and_opsengine_integration() -> None:
    ql = headers(client, "lan")
    
    # 1. First analyze meeting
    analyze_res = client.post(
        "/api/v1/meeting/analyze",
        json={
            "text": "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h.",
            "meeting_type": "giao_ca",
            "audio_source": "google_meet_tab",
        },
        headers=ql,
    ).json()

    # 2. Apply the approved meeting
    apply_res = client.post(
        "/api/v1/meeting/apply",
        json=analyze_res,
        headers=ql,
    )
    assert apply_res.status_code == 200, apply_res.text
    apply_body = apply_res.json()
    assert apply_body["ok"] is True
    assert apply_body["tasks_created"] >= 1

    # 3. Verify tasks are now in opsengine treo
    treo_items = kv_get("treo", [])
    assert any("Tuấn" in str(item) for item in treo_items)

    # 4. Verify meeting is listed in meetings history
    list_res = client.get("/api/v1/meetings", headers=ql)
    assert list_res.status_code == 200
    meetings = list_res.json()["items"]
    assert len(meetings) >= 1
    assert meetings[0]["id"] == analyze_res["id"]


def test_meeting_apply_records_sop_proposals() -> None:
    """Regression: apply phải ghi nhận SOP đã duyệt (signature record_sua cũ từng nuốt mất)."""
    from ca_api.persist import reset_init_flag

    reset_init_flag()  # cô lập store (fixture autouse cũng set, nhưng an toàn)
    ql = headers(client, "lan")
    analyze = client.post(
        "/api/v1/meeting/analyze",
        json={
            "text": "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h. My đổi định lượng trà đào sang 20ml.",
            "meeting_type": "giao_ca",
            "audio_source": "google_meet_tab",
        },
        headers=ql,
    ).json()

    # Force SOP proposal da_duyet để test apply ghi nhận đề xuất
    sop = analyze.get("de_xuat_sop") or []
    for s in sop:
        s["buoc_so"] = 3

    apply_res = client.post("/api/v1/meeting/apply", json=analyze, headers=ql)
    assert apply_res.status_code == 200, apply_res.text
    body = apply_res.json()
    assert body["ok"] is True
    assert body["sop_proposals"] >= 1, f"Expected sop_proposals>=1, got {body['sop_proposals']}"


def test_meeting_delete() -> None:
    """Xoá cuộc họp: quản lý được, không tồn tại -> 404."""
    ql = headers(client, "lan")
    analyze = client.post(
        "/api/v1/meeting/analyze",
        json={
            "text": "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h.",
            "meeting_type": "giao_ca",
            "audio_source": "google_meet_tab",
        },
        headers=ql,
    ).json()
    mid = analyze["id"]

    # Chưa apply nên chưa có trong meetings -> delete trả 404 (vì chưa lưu).
    # Apply trước rồi delete.
    client.post("/api/v1/meeting/apply", json=analyze, headers=ql)

    del_res = client.delete(f"/api/v1/meetings/{mid}", headers=ql)
    assert del_res.status_code == 200, del_res.text
    assert del_res.json()["ok"] is True

    # Xoá lần nữa -> 404
    del_res2 = client.delete(f"/api/v1/meetings/{mid}", headers=ql)
    assert del_res2.status_code == 404


def _meeting_co_de_xuat_sop() -> dict:
    return {
        "id": "m_sop_01",
        "tieu_de": "Họp giao ca sáng",
        "loai_hop": "giao_ca",
        "tom_tat": "Đổi định lượng trà đào.",
        "de_xuat_sop": [
            {
                "quy_trinh_lien_quan": "tra_dao",
                "buoc_so": 2,
                "noi_dung_thay_doi": "Giảm định lượng đào từ 30ml xuống 20ml.",
                "ly_do": "Khách kêu ngọt quá.",
            }
        ],
        "de_xuat_phe_duyet": [
            {
                "id": "dx_01",
                "loai_de_xuat": "quy_trinh_sop",
                "tieu_de": "Thêm bước kiểm ron máy pha",
                "noi_dung": "Kiểm tra ron máy pha số 2 mỗi cuối ca.",
                "trang_thai": "da_duyet",
                "quy_trinh_lien_quan": "dong_quan",
                "buoc_so": 3,
            },
            {
                "id": "dx_02",
                "loai_de_xuat": "mua_sam_vat_tu",
                "tieu_de": "Mua thêm ly",
                "noi_dung": "Không phải SOP — phải bị bỏ qua.",
                "trang_thai": "da_duyet",
            },
        ],
    }


def test_meeting_apply_luu_de_xuat_sop_that() -> None:
    """Đề xuất SOP đã duyệt phải được lưu thật — không còn im lặng mất hút."""
    ql = headers(client, "lan")
    body = _meeting_co_de_xuat_sop()

    res = client.post("/api/v1/meeting/apply", json=body, headers=ql)
    assert res.status_code == 200, res.text
    # 1 từ de_xuat_sop + 1 de_xuat_phe_duyet loại quy_trinh_sop (mua_sam_vat_tu bị bỏ qua)
    assert res.json()["sop_proposals"] == 2

    got = client.get("/api/v1/sop/de-xuat", headers=ql)
    assert got.status_code == 200
    items = got.json()["items"]
    assert len(items) == 2
    noi_dung = {x["noi_dung"] for x in items}
    assert "Giảm định lượng đào từ 30ml xuống 20ml." in noi_dung
    assert "Kiểm tra ron máy pha số 2 mỗi cuối ca." in noi_dung
    assert all(x["meeting_id"] == "m_sop_01" for x in items)
    assert all("ly_do" in x and x["ly_do"] for x in items)

    # Apply lại cùng cuộc họp — không nhân đôi bản ghi
    res2 = client.post("/api/v1/meeting/apply", json=body, headers=ql)
    assert res2.json()["sop_proposals"] == 0
    assert len(client.get("/api/v1/sop/de-xuat", headers=ql).json()["items"]) == 2


def test_sop_de_xuat_can_dang_nhap() -> None:
    res = client.get("/api/v1/sop/de-xuat")
    assert res.status_code == 401
