"""Mã lý do phân công — lõi tất định, không LLM (§13.1)."""

from __future__ import annotations

import pytest
from ca_solver.explain import (
    MA_LY_DO,
    MA_VO_NGHIEM,
    LyDo,
    sinh_ly_do,
    sinh_ly_do_toan_lich,
)
from ca_solver.model import LichInput

BASE = {"tran_gio_tuan": 48.0, "khoang_nghi_gio": 12.0}


def _lich(**kw: object) -> LichInput:
    data: dict[str, object] = {
        "nhan_vien_ids": ["nv_01", "nv_02"],
        "ca_ids": ["c1"],
        "phan_cong": {"c1": ["nv_01"]},
        "ca_meta": {"c1": {"thu": "T7", "bat_dau": "13:00", "ket_thuc": "18:00", "ngay": "T7"}},
        "so_nguoi_toi_thieu": {"c1": 3},
        "ky_nang": {"nv_01": {"pha_che"}, "nv_02": set()},
        "vi_tri_can": {"c1": "pha_che"},
        **BASE,
    }
    data.update(kw)
    return LichInput(**data)  # type: ignore[arg-type]


# ── Từ điển ───────────────────────────────────────────────────────────────


def test_tu_dien_khong_rong() -> None:
    assert MA_LY_DO
    assert MA_VO_NGHIEM


def test_cum_tu_khong_chua_chu_so() -> None:
    """Số chỉ được vào câu qua AG-EXPLAIN.DUOI_SO, nên cụm từ gốc phải sạch số."""
    for ma, cum in MA_LY_DO.items():
        assert not any(c.isdigit() for c in cum), f"{ma} có chữ số trong cụm từ"


def test_ma_vo_nghiem_tach_khoi_ma_thuong() -> None:
    assert set(MA_LY_DO) & set(MA_VO_NGHIEM) == set()


def test_ly_do_tu_choi_ma_la() -> None:
    with pytest.raises(ValueError, match="ma_ly_do_khong_ton_tai"):
        LyDo("MA_KHONG_CO_THAT")


def test_ly_do_nhan_ma_vo_nghiem() -> None:
    assert LyDo("THIEU_NGUOI_KY_NANG").ma == "THIEU_NGUOI_KY_NANG"


# ── Sinh mã theo dữ liệu ──────────────────────────────────────────────────


def test_ky_nang_khop_khi_co_ky_nang() -> None:
    r = sinh_ly_do(_lich(), "c1", "nv_01")
    assert "KY_NANG_KHOP" in r.ma_list()


def test_khong_phat_ky_nang_khi_thieu() -> None:
    r = sinh_ly_do(_lich(phan_cong={"c1": ["nv_02"]}), "c1", "nv_02")
    assert "KY_NANG_KHOP" not in r.ma_list()


def test_khong_trung_tkb_chi_phat_khi_co_khai_tkb() -> None:
    khong = sinh_ly_do(_lich(), "c1", "nv_01")
    assert "KHONG_TRUNG_TKB" not in khong.ma_list()

    co = sinh_ly_do(_lich(tkb={"nv_01": [("T2", "07:00", "10:00")]}), "c1", "nv_01")
    assert "KHONG_TRUNG_TKB" in co.ma_list()


def test_nghi_phep_chan_ma_khong_nghi_phep() -> None:
    r = sinh_ly_do(_lich(nghi_phep={("nv_01", "T7")}), "c1", "nv_01")
    assert "KHONG_NGHI_PHEP" not in r.ma_list()


def test_con_tran_gio_mang_hai_so() -> None:
    r = sinh_ly_do(_lich(gio_da_lam={"nv_01": 20.0}), "c1", "nv_01")
    ly = next(d for d in r.ly_do if d.ma == "CON_TRAN_GIO")
    assert ly.so_lieu == ["20", "48"]


def test_het_tran_gio_khong_phat_ma() -> None:
    r = sinh_ly_do(_lich(gio_da_lam={"nv_01": 48.0}), "c1", "nv_01")
    assert "CON_TRAN_GIO" not in r.ma_list()


def test_du_khoang_nghi_mang_so_cau_hinh() -> None:
    r = sinh_ly_do(_lich(), "c1", "nv_01")
    ly = next(d for d in r.ly_do if d.ma == "DU_KHOANG_NGHI")
    assert ly.so_lieu == ["12"]


def test_ca_can_them_nguoi_mang_dinh_muc() -> None:
    r = sinh_ly_do(_lich(), "c1", "nv_01")
    ly = next(d for d in r.ly_do if d.ma == "CA_CAN_THEM_NGUOI")
    assert ly.so_lieu == ["3"]


# ── Nợ công bằng ──────────────────────────────────────────────────────────


def test_no_cong_bang_cao_khi_tren_trung_vi() -> None:
    debt = {
        "nv_01": {"cuoi_tuan": 9.0},
        "nv_02": {"cuoi_tuan": 1.0},
        "nv_03": {"cuoi_tuan": 2.0},
    }
    r = sinh_ly_do(_lich(debt=debt), "c1", "nv_01")
    assert "NO_CONG_BANG_CAO" in r.ma_list()


def test_no_cong_bang_thap_khi_duoi_trung_vi() -> None:
    debt = {
        "nv_01": {"cuoi_tuan": 0.0},
        "nv_02": {"cuoi_tuan": 5.0},
        "nv_03": {"cuoi_tuan": 6.0},
    }
    r = sinh_ly_do(_lich(debt=debt), "c1", "nv_01")
    assert "NO_CONG_BANG_THAP" in r.ma_list()


def test_khong_co_debt_thi_khong_phat_ma_no() -> None:
    r = sinh_ly_do(_lich(debt={}), "c1", "nv_01")
    assert not {"NO_CONG_BANG_CAO", "NO_CONG_BANG_THAP"} & set(r.ma_list())


# ── Bất biến ──────────────────────────────────────────────────────────────


def test_moi_ma_deu_co_trong_tu_dien() -> None:
    r = sinh_ly_do(_lich(gio_da_lam={"nv_01": 10.0}), "c1", "nv_01")
    for ma in r.ma_list():
        assert ma in MA_LY_DO


def test_so_lieu_cho_phep_la_hop_cua_cac_ma() -> None:
    r = sinh_ly_do(_lich(gio_da_lam={"nv_01": 20.0}), "c1", "nv_01")
    assert {"20", "48", "12", "3"} <= r.so_lieu_cho_phep()


def test_tat_dinh_cung_dau_vao_cung_ket_qua() -> None:
    a = sinh_ly_do(_lich(gio_da_lam={"nv_01": 20.0}), "c1", "nv_01")
    b = sinh_ly_do(_lich(gio_da_lam={"nv_01": 20.0}), "c1", "nv_01")
    assert a.ma_list() == b.ma_list()
    assert a.so_lieu_cho_phep() == b.so_lieu_cho_phep()


def test_toan_lich_phu_moi_phan_cong() -> None:
    data = _lich(
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01", "nv_02"], "c2": ["nv_01"]},
        ca_meta={
            "c1": {"thu": "T7", "bat_dau": "13:00", "ket_thuc": "18:00", "ngay": "T7"},
            "c2": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00", "ngay": "T2"},
        },
        so_nguoi_toi_thieu={"c1": 3, "c2": 1},
        vi_tri_can={"c1": "pha_che", "c2": "pha_che"},
    )
    out = sinh_ly_do_toan_lich(data)
    assert {(r.ca_id, r.nhan_vien_id) for r in out} == {
        ("c1", "nv_01"),
        ("c1", "nv_02"),
        ("c2", "nv_01"),
    }


def test_lich_rong_tra_danh_sach_rong() -> None:
    assert sinh_ly_do_toan_lich(_lich(phan_cong={})) == []
