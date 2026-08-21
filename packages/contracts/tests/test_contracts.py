from __future__ import annotations

from ca_contracts import CONTRACTS, Ca, LichTuan, NhanVien, PhieuMau, RangBuocTrichXuat


def test_five_contracts_registered() -> None:
    assert set(CONTRACTS) == {
        "NhanVien",
        "Ca",
        "LichTuan",
        "PhieuMau",
        "RangBuocTrichXuat",
    }


def test_round_trip_models() -> None:
    nv = NhanVien(id="nv_01", ten="A", ky_nang=["pha_che"])
    ca = Ca(id="c1", ngay="2026-08-21", bat_dau="07:00", ket_thuc="12:00", vi_tri="pha_che")
    lich = LichTuan(tuan_iso="2026-W34", phan_cong={"c1": ["nv_01"]})
    phieu = PhieuMau(ma="mo_quan", ten="Mở quán", buoc=[])
    rb = RangBuocTrichXuat(id="r1", nguon="tkb", noi_dung="học T2 sáng", do_tin_cay=0.8)
    assert nv.id == "nv_01"
    assert ca.so_nguoi_toi_thieu == 1
    assert lich.trang_thai == "nhap"
    assert phieu.ma == "mo_quan"
    assert rb.trang_thai == "cho_duyet"
