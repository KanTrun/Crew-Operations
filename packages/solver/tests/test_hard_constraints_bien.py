"""Nhánh bỏ qua (meta thiếu/khong hợp lệ) của các checker cứng c01, c03, c04, c06."""

from __future__ import annotations

from ca_solver.constraints import c01, c03, c04, c06
from ca_solver.model import LichInput


def test_c01_bo_qua_ca_khong_co_meta() -> None:
    """Ca được phân công nhưng không có ca_meta thì c01 bỏ qua, không nổ KeyError."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1"],
        phan_cong={"c1": ["nv_01"]},
        ca_meta={},
        tkb={"nv_01": [("T2", "08:00", "10:00")]},
    )
    assert c01.check(data) == []


def test_c01_bo_qua_meta_thieu_gio_ket_thuc() -> None:
    """Meta có thứ nhưng thiếu ket_thuc thì không đủ dữ liệu để so trùng TKB."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1"],
        phan_cong={"c1": ["nv_01"]},
        ca_meta={"c1": {"thu": "T2", "bat_dau": "07:00"}},
        tkb={"nv_01": [("T2", "08:00", "10:00")]},
    )
    assert c01.check(data) == []


def test_c01_bo_qua_meta_thieu_thu() -> None:
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1"],
        phan_cong={"c1": ["nv_01"]},
        ca_meta={"c1": {"bat_dau": "07:00", "ket_thuc": "12:00"}},
        tkb={"nv_01": [("T2", "08:00", "10:00")]},
    )
    assert c01.check(data) == []


def test_c03_bo_qua_ca_dau_thieu_gio() -> None:
    """Ca đứng trước thiếu bat_dau/ket_thuc thì c03 bỏ qua cả cặp."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
        ca_meta={
            "c1": {"thu": "T2"},
            "c2": {"thu": "T2", "bat_dau": "10:00", "ket_thuc": "15:00"},
        },
    )
    assert c03.check(data) == []


def test_c03_bo_qua_ca_sau_thieu_gio() -> None:
    """Ca đứng sau cùng thứ nhưng thiếu giờ thì không kết luận trùng ca."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
        ca_meta={
            "c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"},
            "c2": {"thu": "T2", "ket_thuc": "15:00"},
        },
    )
    assert c03.check(data) == []


def test_c03_khac_thu_khong_tinh_trung_ca() -> None:
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
        ca_meta={
            "c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"},
            "c2": {"thu": "T3", "bat_dau": "10:00", "ket_thuc": "15:00"},
        },
    )
    assert c03.check(data) == []


def test_c04_bo_qua_ca_khong_co_meta() -> None:
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
        ca_meta={"c2": {"thu": "T3", "bat_dau": "07:00", "ket_thuc": "12:00"}},
        khoang_nghi_gio=12.0,
    )
    assert c04.check(data) == []


def test_c04_bo_qua_thu_khong_hop_le() -> None:
    """Thứ không nằm trong bảng T2..CN thì không xếp được lên trục thời gian."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
        ca_meta={
            "c1": {"thu": "T9", "bat_dau": "07:00", "ket_thuc": "22:00"},
            "c2": {"thu": "T3", "bat_dau": "07:00", "ket_thuc": "12:00"},
        },
        khoang_nghi_gio=12.0,
    )
    assert c04.check(data) == []


def test_c04_dung_bien_khoang_nghi_thi_dat() -> None:
    """Nghỉ đúng bằng khoang_nghi_gio là hợp lệ, chỉ thiếu hơn mới vi phạm."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1", "c2"],
        phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
        ca_meta={
            "c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "19:00"},
            "c2": {"thu": "T3", "bat_dau": "07:00", "ket_thuc": "12:00"},
        },
        khoang_nghi_gio=12.0,
    )
    assert c04.check(data) == []


def test_c06_bo_qua_ca_khong_co_meta() -> None:
    """Ca không có meta thì c06 không biết thứ nào nên bỏ qua, không báo trùng phép."""
    data = LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1"],
        phan_cong={"c1": ["nv_01"]},
        ca_meta={},
        nghi_phep={("nv_01", "")},
    )
    assert c06.check(data) == []
