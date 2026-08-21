"""Shared data contracts — source of truth (Sprint 1 expands to five schemas)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NhanVien(BaseModel):
    id: str
    ten: str
    ky_nang: list[str] = Field(default_factory=list)


class Ca(BaseModel):
    id: str
    bat_dau: str
    ket_thuc: str
    so_nguoi_toi_thieu: int = 1


class LichTuan(BaseModel):
    tuan_iso: str
    phan_cong: dict[str, str] = Field(default_factory=dict)


class PhieuBuoc(BaseModel):
    ma: str
    ten: str
    minh_chung: str = "khong"


class RangBuocTrichXuat(BaseModel):
    nguon: str
    noi_dung: str
    do_tin_cay: float
    trang_thai: str = "cho_duyet"
