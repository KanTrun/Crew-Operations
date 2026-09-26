"""VF-NUM — every number in a sentence must exist in source data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_NUM = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class NumResult:
    passed: bool
    numbers: list[str]
    missing: list[str]
    reason: str = ""


def validate_num(text: str, allowed: set[str] | list[Any]) -> NumResult:
    pool = {str(x).replace(",", ".") for x in allowed}
    found = _NUM.findall(text or "")
    missing = []
    for raw in found:
        key = raw.replace(",", ".")
        if key not in pool and raw not in pool:
            missing.append(raw)
    ok = not missing
    return NumResult(
        passed=ok,
        numbers=found,
        missing=missing,
        reason="" if ok else "so_khong_co_trong_du_lieu",
    )


# ── Phát hiện mâu thuẫn số liệu giữa hai ca (VF-NUM mở rộng) ──────────────────

# Chủ đề số liệu thường gặp trong bàn giao ca. Mỗi chủ đề gom mọi con số xuất
# hiện quanh từ khoá để so lệch. Tất định, không LLM (ADR-002).
_CHU_DE_TU_KHOA: dict[str, tuple[str, ...]] = {
    "ket": ("két", "ket", "tiền mặt", "tien mat"),
    "doanh_thu": ("doanh thu", "doanh_thu", "bán được", "thu được"),
    "chi_phi": ("chi phí", "chi phi", "đã chi", "mua"),
    "hao_hut": ("hao hụt", "hao hut", "hao phí", "hao phi", "bỏ", "hủy"),
}
# Số tiền: 1.234.567 / 1,234,567 / 1234567 (>= 4 chữ số để tránh "3 bàn", "2 người").
_SO_TIEN = re.compile(r"\d{1,3}(?:[.,]\d{3}){1,}|\d{4,}")


@dataclass
class NumberConflict:
    """Hai con số khác nhau cho cùng một chủ đề trong bàn giao."""

    chu_de: str
    gia_tri: list[int]
    cau: list[str]


def _chuan_hoa_so_tien(raw: str) -> int:
    """'2.350.000' / '2,350,000' / '2350000' → 2350000 (tất định)."""
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else 0


def detect_number_conflicts(text: str) -> list[NumberConflict]:
    """Tìm các chủ đề có ≥2 giá trị tiền KHÁC nhau trong cùng bàn giao.

    Đây là cổng VF-NUM mở rộng: thay vì chỉ kiểm "số có trong nguồn không",
    nó phát hiện *hai ca khai lệch nhau* về cùng một chủ đề (ví dụ ca sáng nói
    két 2.350.000đ, ca chiều nói 2.300.000đ) — đúng ADR-008: nêu ra cho người
    quyết, không tự chọn bên nào.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    gom: dict[str, dict[int, set[str]]] = {}
    for ln in lines:
        low = ln.lower()
        for chu_de, tu_khoa in _CHU_DE_TU_KHOA.items():
            if not any(tk in low for tk in tu_khoa):
                continue
            for raw in _SO_TIEN.findall(ln):
                gia_tri = _chuan_hoa_so_tien(raw)
                if gia_tri <= 0:
                    continue
                gom.setdefault(chu_de, {}).setdefault(gia_tri, set()).add(ln)

    conflicts: list[NumberConflict] = []
    for chu_de, by_value in gom.items():
        if len(by_value) < 2:
            continue
        all_cau: set[str] = set()
        for cau_set in by_value.values():
            all_cau |= cau_set
        conflicts.append(
            NumberConflict(
                chu_de=chu_de,
                gia_tri=sorted(by_value.keys()),
                cau=sorted(all_cau),
            )
        )
    return conflicts
