"""c06 — ngày đã duyệt nghỉ phép."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_solver.model import LichInput


def check(data: LichInput) -> list[str]:
    out: list[str] = []
    for ca_id, nvs in data.phan_cong.items():
        m = data.ca_meta.get(ca_id)
        if not m:
            continue
        thu = m.get("thu", "")
        for nv in nvs:
            if (nv, thu) in data.nghi_phep:
                out.append(f"c06:{ca_id}:{nv}:trung_nghi_phep")
    return out
