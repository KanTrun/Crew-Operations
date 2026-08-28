"""Nhánh biên của fairness debt: ca vụn, max_debt, debt_spread rỗng."""

from __future__ import annotations

from ca_solver.fairness import (
    AXES,
    debt_spread,
    max_debt,
    update_debt_from_assignment,
    zero_debt,
)


def test_fairness_ca_vun_duoi_5_gio_cong_truc_vun() -> None:
    """Ca ngắn hơn 5 giờ phải cộng 1 vào trục 'vun'."""
    debt = zero_debt(["nv_01"])
    out = update_debt_from_assignment(
        debt,
        {"c1": ["nv_01"]},
        {"c1": {"thu": "T2", "khung": "sang", "bat_dau": "07:00", "ket_thuc": "10:00"}},
    )
    assert out["nv_01"]["vun"] == 1.0
    assert out["nv_01"]["gio"] == 3.0


def test_fairness_ca_du_5_gio_khong_tinh_la_ca_vun() -> None:
    """Đúng biên 5 giờ thì không được coi là ca vụn."""
    out = update_debt_from_assignment(
        zero_debt(["nv_01"]),
        {"c1": ["nv_01"]},
        {"c1": {"thu": "T2", "khung": "sang", "bat_dau": "07:00", "ket_thuc": "12:00"}},
    )
    assert out["nv_01"]["vun"] == 0.0
    assert out["nv_01"]["gio"] == 5.0


def test_max_debt_tra_ve_gia_tri_lon_nhat_moi_truc() -> None:
    debt = {
        "nv_01": {"cuoi_tuan": 1.0, "dem": 2.0, "gio": 7.5, "vun": 0.0},
        "nv_02": {"cuoi_tuan": 3.0, "dem": 0.0, "gio": 4.0, "vun": 1.0},
    }
    assert max_debt(debt) == 7.5


def test_max_debt_debt_rong_tra_ve_khong() -> None:
    """Không có ai trong bảng nợ thì max_debt phải là 0.0, không lỗi."""
    assert max_debt({}) == 0.0


def test_max_debt_bo_qua_truc_thieu_thay_bang_khong() -> None:
    """Bảng nợ thiếu trục vẫn tính được, trục thiếu coi như 0."""
    assert max_debt({"nv_01": {"gio": 2.0}}) == 2.0


def test_debt_spread_rong_tra_ve_khong() -> None:
    """debt_spread trên bảng nợ rỗng phải trả 0.0 chứ không ném lỗi."""
    assert debt_spread({}) == 0.0


def test_debt_spread_mot_nguoi_bang_khong() -> None:
    """Chỉ một người thì max == min nên spread = 0."""
    debt = {"nv_01": {a: 1.0 for a in AXES}}
    assert debt_spread(debt) == 0.0
