"""c01 — không trùng giờ học (TKB)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_solver.model import LichInput


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _overlap(a0: str, a1: str, b0: str, b1: str) -> bool:
    return _to_min(a0) < _to_min(b1) and _to_min(b0) < _to_min(a1)


def check(data: LichInput) -> list[str]:
    out: list[str] = []
    for ca_id, nvs in data.phan_cong.items():
        meta = data.ca_meta.get(ca_id)
        if not meta:
            continue
        thu = meta.get("thu")
        bat = meta.get("bat_dau")
        ket = meta.get("ket_thuc")
        if not thu or not bat or not ket:
            continue
        for nv in nvs:
            for block in data.tkb.get(nv, []):
                b_thu, b0, b1 = block
                if b_thu == thu and _overlap(bat, ket, b0, b1):
                    out.append(f"c01:{ca_id}:{nv}:trung_tkb")
    return out
