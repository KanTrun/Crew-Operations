"""c05 — trần giờ tuần."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_solver.model import LichInput


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def check(data: LichInput) -> list[str]:
    hours: dict[str, float] = defaultdict(float)
    hours.update({k: float(v) for k, v in data.gio_da_lam.items()})
    for ca_id, nvs in data.phan_cong.items():
        m = data.ca_meta.get(ca_id)
        if not m or "bat_dau" not in m or "ket_thuc" not in m:
            continue
        dur = (_to_min(m["ket_thuc"]) - _to_min(m["bat_dau"])) / 60.0
        for nv in nvs:
            hours[nv] += dur
    out: list[str] = []
    for nv, h in hours.items():
        if h > data.tran_gio_tuan:
            out.append(f"c05:{nv}:vuot_tran_tuan:{h}")
    return out
