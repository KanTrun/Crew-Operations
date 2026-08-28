"""Shared data contracts — Sprint-1 schemas plus quầy nội bộ (ADR-013)."""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from typing import Literal

from pydantic import BaseModel, Field


class NhanVien(BaseModel):
    id: str
    ten: str
    ky_nang: list[str] = Field(default_factory=list)
    la_sinh_vien: bool = True
    so_dien_thoai_hash: str | None = None


class Ca(BaseModel):
    id: str
    ngay: str
    bat_dau: str
    ket_thuc: str
    vi_tri: str
    so_nguoi_toi_thieu: int = 1


class LichTuan(BaseModel):
    tuan_iso: str
    trang_thai: Literal["nhap", "dang_giai", "cho_duyet", "da_cong_bo", "da_dong"] = "nhap"
    phan_cong: dict[str, list[str]] = Field(
        default_factory=dict,
        description="ca_id -> danh sách nhan_vien_id",
    )


class MinhChungLoai(StrEnum):
    khong = "khong"
    so = "so"
    anh = "anh"
    kiem_ke = "kiem_ke"
    van_ban = "van_ban"
    danh_sach = "danh_sach"
    xac_nhan = "xac_nhan"
    xac_nhan_doc = "xac_nhan_doc"


class PhieuBuoc(BaseModel):
    ma: str
    ten: str
    minh_chung: MinhChungLoai = MinhChungLoai.khong


class PhieuMau(BaseModel):
    ma: str
    ten: str
    gan_voi: str | None = None
    buoc: list[PhieuBuoc]


class RangBuocTrichXuat(BaseModel):
    id: str
    nguon: Literal["tkb", "tin_nhan", "ban_giao", "khac"]
    nhan_vien_id: str | None = None
    noi_dung: str
    do_tin_cay: float = Field(ge=0.0, le=1.0)
    trang_thai: Literal["cho_duyet", "da_duyet", "tu_choi"] = "cho_duyet"
    khung_gio: list[str] = Field(default_factory=list)


class DongDon(BaseModel):
    mon_id: str
    ten: str
    so_luong: int = Field(ge=1)
    gia: int = Field(ge=0)


class MonNuoc(BaseModel):
    id: str
    ten: str
    gia: int = Field(ge=0, description="Đồng, số nguyên")
    an: bool = False
    bom: dict[str, float] = Field(
        default_factory=dict,
        description="Nguyên liệu ước lượng khi hoàn thành đơn, vd cafe_g, sua_ml, ly",
    )


class DonQuay(BaseModel):
    id: str
    nv_id: str
    trang_thai: Literal["cho_pha", "dang_pha", "xong", "huy"] = "cho_pha"
    thanh_toan: Literal["tien_mat", "da_ck", "chua_thu"] = "chua_thu"
    dong: list[DongDon]
    ly_do_huy: str | None = None
    nguon: Literal["quay_noi_bo"] = "quay_noi_bo"
    luc: str = ""


CONTRACTS = {
    "NhanVien": NhanVien,
    "Ca": Ca,
    "LichTuan": LichTuan,
    "PhieuMau": PhieuMau,
    "RangBuocTrichXuat": RangBuocTrichXuat,
    "MonNuoc": MonNuoc,
    "DonQuay": DonQuay,
    "DongDon": DongDon,
}
