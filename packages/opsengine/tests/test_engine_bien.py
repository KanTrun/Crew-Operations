"""Nhánh lỗi và biên của ops engine: chặn mở phiếu, sai thứ tự, minh chứng, ngưỡng."""

from __future__ import annotations

import pytest
from ca_ops import PhieuRun, add_treo, complete_buoc, escalate, load_template, start_phieu

PHOTO = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="


def _gia_tri(minh_chung: str) -> object:
    if minh_chung == "anh":
        return PHOTO
    if minh_chung in {"so", "kiem_ke"}:
        return "4"
    return True


def _mo_quan(now_ms: int = 0) -> PhieuRun:
    return start_phieu(
        run_id="p_bien",
        mau="mo_quan",
        nv_id="nv_01",
        ca_id="w1_c01",
        now_ms=now_ms,
        diem_danh=True,
    )


def _di_den(run: PhieuRun, den_ma: str, *, t0: int = 5000) -> int:
    """Hoàn thành các bước hợp lệ cho tới khi bước hiện tại là ``den_ma``."""
    t = t0
    while True:
        cur = run.current()
        assert cur is not None, f"khong toi duoc buoc {den_ma}"
        if cur.ma == den_ma:
            return t
        complete_buoc(run, cur.ma, _gia_tri(cur.minh_chung), t)
        t += 5000


def test_load_template_khong_ton_tai_bao_loi() -> None:
    with pytest.raises(FileNotFoundError):
        load_template("mau_khong_he_ton_tai")


def test_start_phieu_chua_diem_danh_bi_chan() -> None:
    """Mẫu mở khi 'nhan_vien_da_diem_danh' phải fail-closed nếu chưa điểm danh."""
    with pytest.raises(PermissionError, match="chua_diem_danh"):
        start_phieu(
            run_id="p1",
            mau="mo_quan",
            nv_id="nv_01",
            ca_id="w1_c01",
            now_ms=0,
            diem_danh=False,
        )


def test_start_phieu_mau_khong_yeu_cau_diem_danh_van_mo_duoc() -> None:
    """Mẫu bàn giao ca mở khi 'ca_ket_thuc' nên không cần điểm danh."""
    run = start_phieu(
        run_id="p2",
        mau="ban_giao_ca",
        nv_id="nv_01",
        ca_id="w1_c01",
        now_ms=0,
        diem_danh=False,
    )
    assert run.buoc


def test_complete_buoc_khi_phieu_da_dong_bi_tu_choi() -> None:
    run = start_phieu(
        run_id="p3",
        mau="ban_giao_ca",
        nv_id="nv_01",
        ca_id="w1_c01",
        now_ms=0,
        diem_danh=False,
    )
    t = 5000
    while True:
        cur = run.current()
        if cur is None:
            break
        complete_buoc(run, cur.ma, _gia_tri(cur.minh_chung), t)
        t += 5000
    assert run.closed
    with pytest.raises(RuntimeError, match="phieu_da_dong"):
        complete_buoc(run, "dang_the_nao", "lai", t)


def test_complete_buoc_sai_thu_tu_bi_tu_choi() -> None:
    run = _mo_quan()
    with pytest.raises(ValueError, match="sai_thu_tu_buoc"):
        complete_buoc(run, "bat_den", True, 5000)


def test_complete_buoc_thieu_minh_chung_anh_bi_tu_choi() -> None:
    run = _mo_quan()
    t = _di_den(run, "ve_sinh_quay")
    with pytest.raises(ValueError, match="thieu_minh_chung_anh"):
        complete_buoc(run, "ve_sinh_quay", True, t)


def test_complete_buoc_anh_khong_phai_chuoi_bi_tu_choi() -> None:
    """Payload ảnh không phải chuỗi thì _is_photo_payload trả False."""
    run = _mo_quan()
    t = _di_den(run, "ve_sinh_quay")
    with pytest.raises(ValueError, match="thieu_minh_chung_anh"):
        complete_buoc(run, "ve_sinh_quay", 12345, t)


def test_complete_buoc_anh_sai_tien_to_data_image_bi_tu_choi() -> None:
    run = _mo_quan()
    t = _di_den(run, "ve_sinh_quay")
    with pytest.raises(ValueError, match="thieu_minh_chung_anh"):
        complete_buoc(run, "ve_sinh_quay", "anh_quay.jpg", t)


def test_complete_buoc_anh_thieu_dau_phay_bi_tu_choi() -> None:
    """Đúng tiền tố nhưng không có dấu phẩy tách base64 vẫn phải trượt."""
    run = _mo_quan()
    t = _di_den(run, "ve_sinh_quay")
    with pytest.raises(ValueError, match="thieu_minh_chung_anh"):
        complete_buoc(run, "ve_sinh_quay", "data:image/png;base64", t)


def test_complete_buoc_anh_base64_qua_ngan_bi_tu_choi() -> None:
    """Phần base64 dưới 8 ký tự là biên dưới, không nhận."""
    run = _mo_quan()
    t = _di_den(run, "ve_sinh_quay")
    with pytest.raises(ValueError, match="thieu_minh_chung_anh"):
        complete_buoc(run, "ve_sinh_quay", "data:image/png;base64,abc", t)


def test_complete_buoc_anh_qua_nhanh_bi_ghi_co() -> None:
    """Bước ảnh xong sau 2 giây (dưới 3s) phải để lại cờ anh_qua_nhanh."""
    run = _mo_quan()
    _di_den(run, "ve_sinh_quay")
    truoc = max(b.completed_at_ms or 0 for b in run.buoc)
    complete_buoc(run, "ve_sinh_quay", PHOTO, truoc + 2000)
    assert "anh_qua_nhanh" in run.anti_fake
    assert "nhanh:ve_sinh_quay" not in run.anti_fake


def test_complete_buoc_gia_tri_khong_phai_so_bi_tu_choi() -> None:
    run = _mo_quan()
    t = _di_den(run, "nhiet_do_tu_lanh")
    with pytest.raises(ValueError, match="gia_tri_khong_phai_so"):
        complete_buoc(run, "nhiet_do_tu_lanh", "am am", t)


def test_complete_buoc_duoi_nguong_bi_ghi_co() -> None:
    """Nhiệt độ tủ lạnh 1 độ dưới ngưỡng min=2 nên phải ghi cờ duoi_nguong."""
    run = _mo_quan()
    t = _di_den(run, "nhiet_do_tu_lanh")
    complete_buoc(run, "nhiet_do_tu_lanh", "1", t)
    assert "duoi_nguong:nhiet_do_tu_lanh" in run.anti_fake


def test_complete_buoc_tren_nguong_bi_ghi_co() -> None:
    """Nhiệt độ tủ lạnh 9 độ trên ngưỡng max=8 nên phải ghi cờ tren_nguong."""
    run = _mo_quan()
    t = _di_den(run, "nhiet_do_tu_lanh")
    complete_buoc(run, "nhiet_do_tu_lanh", "9", t)
    assert "tren_nguong:nhiet_do_tu_lanh" in run.anti_fake


def test_complete_buoc_so_dung_dau_phay_thap_phan_van_trong_nguong() -> None:
    """Giá trị '2,5' phải được hiểu là 2.5 và nằm trong ngưỡng 2..8."""
    run = _mo_quan()
    t = _di_den(run, "nhiet_do_tu_lanh")
    complete_buoc(run, "nhiet_do_tu_lanh", "2,5", t)
    assert not [x for x in run.anti_fake if "nguong" in x]


def test_add_treo_rong_bi_tu_choi() -> None:
    run = _mo_quan()
    with pytest.raises(ValueError, match="treo_rong"):
        add_treo(run, "   ")
    assert run.treo == []


def test_escalate_qua_hai_lan_han_bao_chu_quan() -> None:
    run = _mo_quan()
    assert escalate(run, now_ms=61 * 60_000) == "bao_chu_quan"


def test_escalate_dung_bien_han_chua_nhac() -> None:
    """Đúng 30 phút chưa vượt hạn nên không escalate."""
    run = _mo_quan()
    assert escalate(run, now_ms=30 * 60_000) is None
