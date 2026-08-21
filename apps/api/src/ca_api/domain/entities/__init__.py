"""Domain entities — pure, no infrastructure imports."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NhanVien:
    id: str
    ten: str
    ky_nang: tuple[str, ...] = ()
    la_sinh_vien: bool = True


@dataclass(frozen=True)
class Ca:
    id: str
    bat_dau: str
    ket_thuc: str
    vi_tri: str
    so_nguoi_toi_thieu: int = 1


@dataclass
class LichTuan:
    tuan_iso: str
    phan_cong: dict[str, list[str]] = field(default_factory=dict)
    trang_thai: str = "nhap"
