# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Trang "Ca của tôi" — trạng thái rõ ràng, và cổng công bố.

Người dùng phàn nàn: "Nó đang có 2 mục là Nhận và Nhả — UI cũng chẳng thể hiểu
rõ vì cũng chẳng biết nhận hay nhả, rồi khi ca đó đã công bố rồi thì cái nút đó
đâu còn ý nghĩa gì". Ba bài ở đây chốt đúng ba lỗi gốc:

  1. `toi_lich` KHÔNG hề set `trang_thai` cho từng ca → UI so
     `trang_thai === "cua_toi"` luôn sai, nhãn "Ca của bạn" là code chết.
  2. Không có gì phân biệt "ca của tôi" với "ca tôi có thể nhận".
  3. Không có tóm tắt nói tuần đang ở đâu và tôi cần làm gì.
"""

from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get, kv_set
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def _dat_tuan(week: str, trang_thai: str, phan: dict[str, list[str]]) -> None:
    """Dựng tuần ở CẢ ba khoá mà `toi_lich` đọc (`phan_cong` + 2 khoá lifecycle)."""
    kv_set("phan_cong", phan)
    kv_set("phan_cong_by_week", {week: phan})
    kv_set("lich_tuan_lifecycle", {"tuan_iso": week, "trang_thai": trang_thai})
    kv_set("lich_tuan_lifecycle_by_week", {week: {"tuan_iso": week, "trang_thai": trang_thai}})


def test_trang_thai_cua_toi_duoc_set_chu_khong_phai_code_chet() -> None:
    """Ca có tên mình PHẢI mang `trang_thai="cua_toi"`.

    Đây là gốc lỗi: trường này trước đây không bao giờ được sinh ra, nên nhánh
    `mine = c.trang_thai === "cua_toi"` ở UI luôn false.
    """
    week = "2026-W21"
    _dat_tuan(week, "da_cong_bo", {"w1_c01": ["nv_03"], "w1_c02": []})
    r = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh"))
    assert r.status_code == 200, r.text
    body = r.json()

    cua_toi = [c for c in body["ca"] if c["trang_thai"] == "cua_toi"]
    co_the_nhan = [c for c in body["ca"] if c["trang_thai"] == "co_the_nhan"]
    assert [c["id"] for c in cua_toi] == ["w1_c01"]
    # Ca trống còn lại là ca CÓ THỂ NHẬN, tách hẳn khỏi ca của tôi.
    assert "w1_c02" in [c["id"] for c in co_the_nhan]
    # Không ca nào lọt vào cả hai nhóm.
    assert not ({c["id"] for c in cua_toi} & {c["id"] for c in co_the_nhan})


def test_tom_tat_noi_ro_tuan_va_viec_can_lam() -> None:
    """Tóm tắt phải có nhãn trạng thái tuần + câu "cần làm", không chỉ con số."""
    week = "2026-W22"
    _dat_tuan(week, "da_cong_bo", {"w1_c01": ["nv_03"], "w1_c02": []})
    body = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh")).json()
    tt = body["tom_tat"]
    assert tt["tuan_iso"] == week
    assert tt["da_cong_bo"] is True
    assert tt["so_ca_cua_toi"] == 1
    assert tt["so_ca_co_the_nhan"] >= 1
    assert "Đã công bố" in tt["trang_thai_label"]
    # Câu chỉ dẫn phải nói được việc cụ thể, không phải câu chung chung.
    assert "Nhả ca" in tt["can_lam"]
    assert "quản lý xác nhận" in tt["can_lam"]


def test_tom_tat_noi_thang_chua_nhan_duoc_khi_tuan_chua_cong_bo() -> None:
    """Tuần chưa công bố: tóm tắt phải nói CHƯA THỂ nhận/nhả.

    Nếu im lặng thì người dùng bấm nút rồi bị từ chối mà không hiểu vì sao —
    đúng cái họ phàn nàn.
    """
    week = "2026-W23"
    _dat_tuan(week, "nhap", {"w1_c01": ["nv_03"]})
    body = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh")).json()
    tt = body["tom_tat"]
    assert tt["da_cong_bo"] is False
    assert tt["tinh_trang"] == "cho_cong_bo"
    assert "chưa thể nhận/nhả ca" in tt["can_lam"]


def test_tom_tat_khi_chua_duoc_xep_ca_nao() -> None:
    """Chưa có ca nào → tóm tắt nói đúng tình trạng, không bịa "0 ca cần làm"."""
    week = "2026-W24"
    _dat_tuan(week, "nhap", {})
    body = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh")).json()
    tt = body["tom_tat"]
    assert tt["tinh_trang"] == "chua_co_lich"
    assert tt["so_ca_cua_toi"] == 0
    assert "chưa có lịch" in tt["can_lam"]


def test_toi_lich_chi_tra_ca_co_that_trong_seed() -> None:
    """Ca id lạ trong phân công không được bịa thành ca có thể nhận."""
    week = "2026-W25"
    _dat_tuan(week, "da_cong_bo", {"w1_c01": ["nv_03"], "ca_khong_ton_tai": []})
    body = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh")).json()
    ids = [c["id"] for c in body["ca"]]
    assert "w1_c01" in ids
    assert "ca_khong_ton_tai" not in ids


def test_rang_buoc_da_duyet_duoc_tra_ve() -> None:
    """Ràng buộc đã duyệt của CHÍNH tôi phải có trong response (UI đã bỏ sót)."""
    week = "2026-W26"
    _dat_tuan(week, "da_cong_bo", {"w1_c01": ["nv_03"]})
    kv_set(
        "inbox_rang_buoc",
        [
            {"id": "it1", "y_dinh": "xin_nghi", "trang_thai": "duyet", "nv_id": "nv_03",
             "hieu_luc": {"ghi": "nghỉ T4"}},
            {"id": "it2", "y_dinh": "xin_nghi", "trang_thai": "cho_duyet", "nv_id": "nv_03",
             "hieu_luc": {"ghi": "chưa duyệt"}},
            {"id": "it3", "y_dinh": "xin_nghi", "trang_thai": "duyet", "nv_id": "nv_99",
             "hieu_luc": {"ghi": "của người khác"}},
        ],
    )
    try:
        body = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh")).json()
        ids = [r["id"] for r in body["rang_buoc_da_duyet"]]
        assert ids == ["it1"]
    finally:
        kv_set("inbox_rang_buoc", [])


def test_ca_nhan_truc_tiep_chi_quan_ly() -> None:
    """Nhân viên gọi đường gán ca của quản lý → 403, không ghi gì."""
    week = "2026-W27"
    _dat_tuan(week, "da_cong_bo", {"w1_c01": ["nv_03"], "w1_c02": []})
    r = client.post(
        "/api/v1/ca/nhan-truc-tiep",
        json={"ca_id": "w1_c02", "nv_id": "nv_03"},
        headers=headers(client, "minh"),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "chi_quan_ly_gan_ca"
    assert kv_get("phan_cong", {})["w1_c02"] == []
