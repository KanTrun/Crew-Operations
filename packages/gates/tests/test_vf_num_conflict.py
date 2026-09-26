# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Test VF-NUM mở rộng — phát hiện lệch số giữa các ca trong bàn giao.

Bug #3 (QA 2026-09-26): bàn giao hai ca khai két lệch nhau (2.350.000 vs
2.300.000) nhưng hệ thống không cảnh báo. `detect_number_conflicts` bổ sung
cổng tất định: nêu ra cho người xác minh, KHÔNG tự chọn bên nào (ADR-008).
"""

from __future__ import annotations

from ca_gates import detect_number_conflicts, validate_num
from ca_gates.vf_num import _chuan_hoa_so_tien


def test_chuan_hoa_so_tien_cac_dinh_dang() -> None:
    assert _chuan_hoa_so_tien("2.350.000") == 2350000
    assert _chuan_hoa_so_tien("2,350,000") == 2350000
    assert _chuan_hoa_so_tien("2350000") == 2350000


def test_phat_hien_lech_so_ket() -> None:
    text = (
        "Ca sáng: két còn 2.350.000đ, còn 3 bàn chưa dọn.\n"
        "Ca chiều: két còn 2.300.000đ, máy pha cần vệ sinh."
    )
    conflicts = detect_number_conflicts(text)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.chu_de == "ket"
    assert c.gia_tri == [2300000, 2350000]
    assert len(c.cau) == 2


def test_khong_bao_dong_khi_cung_gia_tri() -> None:
    text = "Ca sáng: két còn 2.350.000đ.\nCa chiều: két còn 2.350.000đ."
    assert detect_number_conflicts(text) == []


def test_bo_qua_so_nho_khong_phai_tien() -> None:
    """'3 bàn', '2 người' không được tính là tiền (số < 4 chữ số)."""
    text = "Ca sáng: 3 bàn chưa dọn.\nCa chiều: 2 bàn chưa dọn."
    assert detect_number_conflicts(text) == []


def test_nhieu_chu_de_cung_luc() -> None:
    text = (
        "Ca sáng: két 2.350.000đ, doanh thu 5.000.000đ.\n"
        "Ca chiều: két 2.300.000đ, doanh thu 5.200.000đ."
    )
    conflicts = {c.chu_de for c in detect_number_conflicts(text)}
    assert conflicts == {"ket", "doanh_thu"}


def test_text_rong_khong_loi() -> None:
    assert detect_number_conflicts("") == []
    assert detect_number_conflicts("Ca sáng bình thường, không có số.") == []


def test_validate_num_van_hoat_dong_nhu_cu() -> None:
    """Không phá vỡ hành vi cũ của validate_num."""
    assert validate_num("còn 15 đơn vị", {"15"}).passed
    assert not validate_num("còn 99 đơn vị", {"15"}).passed
