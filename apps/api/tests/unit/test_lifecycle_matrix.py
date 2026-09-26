# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Hai đường vòng đời lịch phải dùng CHUNG một ma trận chuyển tiếp.

Bối cảnh: `PATCH /api/v1/lich-tuan/lifecycle` (main.py) và
`POST /api/v1/lich/lifecycle` (sprint45.py) là hai cửa vào cùng một state machine.
Trước đây mỗi bên khai một bản ma trận riêng, và chúng ĐÃ LỆCH ở đúng một ô:
`da_cong_bo -> nhap`.

Hệ quả thật: "mở lại lịch đã công bố" chạy được qua POST nhưng trả 409
`illegal:da_cong_bo->nhap` qua PATCH. UI hiện gọi đúng đường nên người dùng chưa
thấy — nhưng bất kỳ client API / test / agent nào chọn nhầm đường đều nhận lỗi cho
một thao tác mà đường kia cho phép. Đó là loại lỗi "lúc được lúc không" khó truy.

Bài này khoá ba điều:
  1. Hai tên ma trận phải là CÙNG MỘT dict (identity), không chỉ bằng giá trị.
     Kiểm identity vì hai dict bằng giá trị vẫn có thể lệch lại ở lần sửa sau.
  2. `da_cong_bo -> nhap` được phép ở CẢ HAI đường (nghiệp vụ thật: quán đổi ca).
  3. Mở lại lịch đã chốt qua PATCH phải đòi lý do, giống POST.
"""

from __future__ import annotations

from ca_api.interfaces.http.main import _LIFECYCLE_ALLOWED, _LIFECYCLE_STATES, app
from ca_api.interfaces.http.sprint45 import _ALLOWED
from ca_api.persist import kv_set
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Một nguồn sự thật
# ─────────────────────────────────────────────────────────────────────────────


def test_hai_duong_vong_doi_dung_chung_mot_dict() -> None:
    """Phải là CÙNG object, không phải hai bản bằng nhau.

    Kiểm `is` chứ không `==`: hai dict bằng giá trị hôm nay vẫn có thể bị sửa
    lệch ở lần cập nhật sau mà không ai phát hiện.
    """
    assert _LIFECYCLE_ALLOWED is _ALLOWED, (
        "main._LIFECYCLE_ALLOWED và sprint45._ALLOWED phải trỏ CÙNG một dict. "
        "Hai bản riêng sẽ lệch lại — đúng lỗi da_cong_bo->nhap đã xảy ra."
    )


def test_moi_trang_thai_deu_co_trong_bang() -> None:
    """Không trạng thái nào được thiếu khoá — thiếu thì `.get(st, set())` im lặng
    trả rỗng, tức mọi chuyển tiếp từ đó đều bị chặn mà không rõ vì sao."""
    for st in _LIFECYCLE_STATES:
        assert st in _LIFECYCLE_ALLOWED, f"thiếu khoá '{st}' trong ma trận"
    # `may_sinh` là trạng thái đầu nhưng KHÔNG nằm trong `_LIFECYCLE_STATES`
    # (đó là danh sách trạng thái UI chọn được) — vẫn phải có trong ma trận.
    assert "may_sinh" in _LIFECYCLE_ALLOWED


def test_khong_co_chuyen_tiep_tu_chinh_no() -> None:
    """Chuyển sang chính trạng thái đang ở là vô nghĩa và che lỗi gọi trùng."""
    for st, dich in _LIFECYCLE_ALLOWED.items():
        assert st not in dich, f"'{st}' không được chuyển sang chính nó"


def test_dich_den_deu_la_trang_thai_hop_le() -> None:
    """Không được trỏ tới trạng thái lạ — bắt lỗi gõ sai tên."""
    hop_le = set(_LIFECYCLE_STATES) | {"may_sinh"}
    for st, dich in _LIFECYCLE_ALLOWED.items():
        la = dich - hop_le
        assert not la, f"'{st}' trỏ tới trạng thái không tồn tại: {sorted(la)}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Ô từng lệch: da_cong_bo -> nhap
# ─────────────────────────────────────────────────────────────────────────────


def test_mo_lai_lich_da_cong_bo_duoc_phep() -> None:
    """Nghiệp vụ thật: lịch đã công bố vẫn phải mở lại được để điều chỉnh."""
    assert "nhap" in _LIFECYCLE_ALLOWED["da_cong_bo"]


def test_patch_lifecycle_chan_mo_lai_da_cong_bo_thieu_ly_do() -> None:
    """PATCH mở lại lịch công bố mà KHÔNG có lý do → 409.

    Ma trận hợp nhất cho `da_cong_bo -> nhap` đi qua, nên cổng lý do phải chặn
    ở đây; nếu không thì mở lại một quyết định đã ban hành sẽ đi qua im lặng.
    """
    week = "2026-W61"
    kv_set("lich_tuan_lifecycle", {"tuan_iso": week, "trang_thai": "da_cong_bo"})
    kv_set(
        "lich_tuan_lifecycle_by_week",
        {week: {"tuan_iso": week, "trang_thai": "da_cong_bo"}},
    )
    r = client.patch(
        "/api/v1/lich-tuan/lifecycle",
        json={"trang_thai": "nhap", "tuan_iso": week},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "mo_lai_phai_co_ly_do"
    # Bất biến: trạng thái KHÔNG được đổi khi bị từ chối.
    from ca_api.persist import kv_get

    assert kv_get("lich_tuan_lifecycle_by_week", {})[week]["trang_thai"] == "da_cong_bo"


def test_post_lifecycle_mo_lai_da_cong_bo_can_ly_do() -> None:
    """POST cùng quy tắc: thiếu lý do → 400 `can_ly_do_mo_lai_lich`."""
    week = "2026-W62"
    kv_set("lich_tuan_lifecycle", {"tuan_iso": week, "trang_thai": "da_cong_bo"})
    kv_set(
        "lich_tuan_lifecycle_by_week",
        {week: {"tuan_iso": week, "trang_thai": "da_cong_bo"}},
    )
    r = client.post(
        "/api/v1/lich/lifecycle",
        json={"to": "nhap", "tuan_iso": week},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "can_ly_do_mo_lai_lich"


def test_post_lifecycle_mo_lai_da_cong_bo_co_ly_do_thanh_cong() -> None:
    """Có lý do → mở lại được, và trạng thái thật sự đổi."""
    from ca_api.persist import kv_get

    week = "2026-W63"
    kv_set("lich_tuan_lifecycle", {"tuan_iso": week, "trang_thai": "da_cong_bo"})
    kv_set(
        "lich_tuan_lifecycle_by_week",
        {week: {"tuan_iso": week, "trang_thai": "da_cong_bo"}},
    )
    r = client.post(
        "/api/v1/lich/lifecycle",
        json={"to": "nhap", "tuan_iso": week, "ly_do": "Quán đổi ca đột xuất"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200, r.text
    assert kv_get("lich_tuan_lifecycle_by_week", {})[week]["trang_thai"] == "nhap"


def test_khong_duoc_nhay_coc_tu_nhap_sang_cong_bo() -> None:
    """`nhap -> da_cong_bo` KHÔNG hợp lệ: phải qua xếp lịch rồi duyệt.

    Chốt lại để việc hợp nhất ma trận không vô tình mở một đường tắt bỏ qua
    bước chạy solver và bước duyệt.
    """
    assert "da_cong_bo" not in _LIFECYCLE_ALLOWED["nhap"]
    assert "da_dong" not in _LIFECYCLE_ALLOWED["nhap"]
