from __future__ import annotations

import pytest
from ca_contracts import (
    CONTRACTS,
    ActionItem,
    Ca,
    CuocHop,
    DeXuatSop,
    DoanThoaiTranscript,
    DongDon,
    DonQuay,
    LichTuan,
    MinhChungLoai,
    MonNuoc,
    NhanVien,
    PhieuMau,
    RangBuocTrichXuat,
)
from pydantic import ValidationError


def test_contracts_registered() -> None:
    assert set(CONTRACTS) == {
        "NhanVien",
        "Ca",
        "LichTuan",
        "PhieuMau",
        "RangBuocTrichXuat",
        "MonNuoc",
        "DonQuay",
        "DongDon",
        "CuocHop",
        "ActionItem",
        "DeXuatSop",
        "DeXuatPheDuyet",
        "GopYLuuY",
        "AuditTuanThuSop",
        "BanTinCaKhan",
        "HuanLuyenQuanLy",
        "CopilotMessage",
        "ActionProposal",
        "PolicyDecision",
    }


def test_round_trip_models() -> None:
    nv = NhanVien(id="nv_01", ten="A", ky_nang=["pha_che"])
    ca = Ca(id="c1", ngay="2026-08-21", bat_dau="07:00", ket_thuc="12:00", vi_tri="pha_che")
    lich = LichTuan(tuan_iso="2026-W34", phan_cong={"c1": ["nv_01"]})
    phieu = PhieuMau(ma="mo_quan", ten="Mở quán", buoc=[])
    rb = RangBuocTrichXuat(id="r1", nguon="tkb", noi_dung="học T2 sáng", do_tin_cay=0.8)
    mon = MonNuoc(id="mon_den", ten="Cà phê đen", gia=25000, bom={"cafe_g": 18, "ly": 1})
    don = DonQuay(
        id="dq_01",
        nv_id="nv_01",
        dong=[DongDon(mon_id="mon_den", ten="Cà phê đen", so_luong=1, gia=25000)],
    )
    assert nv.id == "nv_01"
    assert ca.so_nguoi_toi_thieu == 1
    assert lich.trang_thai == "nhap"
    assert phieu.ma == "mo_quan"
    assert rb.trang_thai == "cho_duyet"
    assert mon.gia == 25000
    assert don.nguon == "quay_noi_bo"
    assert don.dong[0].so_luong == 1


def test_do_tin_cay_rejects_negative() -> None:
    """do_tin_cay nhỏ hơn 0.0 phải ném ValidationError."""
    with pytest.raises(ValidationError):
        RangBuocTrichXuat(id="r1", nguon="tkb", noi_dung="test", do_tin_cay=-0.1)


def test_do_tin_cay_rejects_above_one() -> None:
    """do_tin_cay lớn hơn 1.0 phải ném ValidationError."""
    with pytest.raises(ValidationError):
        RangBuocTrichXuat(id="r1", nguon="tkb", noi_dung="test", do_tin_cay=1.1)


def test_nguon_rejects_invalid_literal() -> None:
    """nguon không thuộc literal cho phép phải ném ValidationError."""
    with pytest.raises(ValidationError):
        RangBuocTrichXuat(id="r1", nguon="facebook", noi_dung="test", do_tin_cay=0.5)  # type: ignore[arg-type]


def test_lich_tuan_rejects_invalid_trang_thai() -> None:
    """trang_thai của LichTuan không thuộc literal cho phép phải ném ValidationError."""
    with pytest.raises(ValidationError):
        LichTuan(tuan_iso="2026-W34", trang_thai="sai")  # type: ignore[arg-type]


def test_minh_chung_loai_has_eight_members() -> None:
    """MinhChungLoai phải có đúng 8 giá trị enum."""
    assert len(MinhChungLoai) == 8


def test_cuoc_hop_model() -> None:
    item = ActionItem(
        id="act_01",
        tieu_de="Lau máy pha cà phê",
        ten_nguoi_nhan="Tuấn",
        nhan_vien_id="nv_01",
        han_chot="22:00",
        muc_do_uu_tien="cao",
        do_tin_cay=0.95,
    )
    meeting = CuocHop(
        id="meet_01",
        tieu_de="Giao ca chiều",
        loai_hop="giao_ca",
        thoi_gian="2026-08-29T20:00:00Z",
        nguon_am_thanh="google_meet_tab",
        transcript_thoai=[
            DoanThoaiTranscript(nguoi_noi="Quản lý", noi_dung="Tuấn nhớ lau máy pha nhé")
        ],
        tom_tat="Nhắc nhở vệ sinh máy pha và chuẩn bị nguyên liệu",
        quyet_dinh=["Vệ sinh máy pha trước 22h"],
        action_items=[item],
        de_xuat_sop=[
            DeXuatSop(
                quy_trinh_lien_quan="Vệ sinh máy",
                noi_dung_thay_doi="Thêm bước xả bột tẩy cặn",
            )
        ],
    )
    assert meeting.id == "meet_01"
    assert len(meeting.action_items) == 1
    assert meeting.action_items[0].ten_nguoi_nhan == "Tuấn"
    assert meeting.trang_thai == "cho_duyet"
