"""AG-BRIEF — bản tin sáng cho chủ quán, tối đa 5 câu.

Ranh giới (§7.1): agent không tính con số nào. Mỗi dữ kiện do lõi tất định
đưa vào kèm tập số của chính nó. Agent xếp thứ tự, cắt còn 5 câu, và **tự loại
câu có số không chứng minh được** trước khi cổng VF-NUM chạy.

Không ghi DB · không gọi agent khác · không quyết định luồng.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_NUM = re.compile(r"\d+(?:[.,]\d+)?")

MAX_CAU = 5

# Thứ tự ưu tiên mặc định khi dữ kiện không tự khai `uu_tien`.
# Số nhỏ = lên trước. Việc có hạn và an toàn đứng trước thông tin nền.
UU_TIEN_LOAI: dict[str, int] = {
    "viec_treo_qua_han": 10,
    "dau_hieu_bat_thuong": 20,
    "ton_duoi_nguong": 30,
    "ca_thieu_nguoi": 40,
    "doi_ca_cho_duyet": 50,
    "phieu_chua_xong": 60,
    "luat_cho_duyet": 70,
}
UU_TIEN_KHAC = 99


@dataclass
class Fact:
    """Một dữ kiện tất định do lõi cấp."""

    loai: str
    cau: str
    so_lieu: list[str] = field(default_factory=list)
    uu_tien: int | None = None

    def thu_tu(self) -> int:
        if self.uu_tien is not None:
            return self.uu_tien
        return UU_TIEN_LOAI.get(self.loai, UU_TIEN_KHAC)


@dataclass
class BriefResult:
    cac_cau: list[str] = field(default_factory=list)
    nguon_loai: list[str] = field(default_factory=list)
    so_lieu_dung: list[str] = field(default_factory=list)
    bi_loai: list[str] = field(default_factory=list)
    loai: str = "ban_tin_sang"

    @property
    def van_ban(self) -> str:
        return " ".join(self.cac_cau)


def _so_hop_le(cau: str, cho_phep: set[str]) -> list[str]:
    """Trả các số trong câu KHÔNG chứng minh được."""
    pool = {str(x).replace(",", ".") for x in cho_phep}
    thieu = []
    for raw in _NUM.findall(cau or ""):
        if raw.replace(",", ".") not in pool and raw not in pool:
            thieu.append(raw)
    return thieu


def viet_ban_tin(facts: list[Fact], *, max_cau: int = MAX_CAU) -> BriefResult:
    """Soạn bản tin sáng từ các dữ kiện.

    Args:
        facts: dữ kiện tất định, mỗi cái mang câu và tập số của nó.
        max_cau: trần số câu, mặc định 5 theo hồ sơ §5.2.

    Returns:
        BriefResult — mọi số trong `cac_cau` đều truy được về `so_lieu` đầu vào.
    """
    out = BriefResult()

    # Sắp xếp tất định: ưu tiên, rồi loại, rồi nội dung câu.
    xep = sorted(facts, key=lambda f: (f.thu_tu(), f.loai, f.cau))

    for f in xep:
        cau = (f.cau or "").strip()
        if not cau:
            out.bi_loai.append(f"{f.loai}:cau_rong")
            continue
        thieu = _so_hop_le(cau, set(f.so_lieu))
        if thieu:
            out.bi_loai.append(f"{f.loai}:so_khong_co_trong_du_lieu:{','.join(thieu)}")
            continue
        if len(out.cac_cau) >= max_cau:
            out.bi_loai.append(f"{f.loai}:vuot_tran_{max_cau}_cau")
            continue
        if not cau.endswith((".", "!", "?")):
            cau += "."
        out.cac_cau.append(cau)
        out.nguon_loai.append(f.loai)
        out.so_lieu_dung.extend(_NUM.findall(cau))

    if not out.cac_cau:
        out.cac_cau = ["Sáng nay không có việc nào cần chủ quán để ý."]
        out.nguon_loai = ["khong_co_du_kien"]

    return out
