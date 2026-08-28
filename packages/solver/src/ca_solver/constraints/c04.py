"""c04 — khoảng nghỉ tối thiểu giữa hai ca."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_solver.model import LichInput

_THU_ORD = {"T2": 0, "T3": 1, "T4": 2, "T5": 3, "T6": 4, "T7": 5, "CN": 6}


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def check(data: LichInput) -> list[str]:
    by_nv: dict[str, list[str]] = defaultdict(list)
    for ca_id, nvs in data.phan_cong.items():
        for nv in nvs:
            by_nv[nv].append(ca_id)
    need = data.khoang_nghi_gio * 60
    out: list[str] = []
    for nv, cas in by_nv.items():
        timed: list[tuple[int, int, str]] = []
        for ca_id in cas:
            m = data.ca_meta.get(ca_id)
            if not m:
                continue
            thu = m.get("thu")
            if thu not in _THU_ORD or "bat_dau" not in m or "ket_thuc" not in m:
                continue
            day = _THU_ORD[thu]
            start = day * 24 * 60 + _to_min(m["bat_dau"])
            end = day * 24 * 60 + _to_min(m["ket_thuc"])
            timed.append((start, end, ca_id))
        timed.sort()
        for i in range(1, len(timed)):
            gap = timed[i][0] - timed[i - 1][1]
            if gap < need:
                out.append(f"c04:{nv}:{timed[i - 1][2]}:{timed[i][2]}:thieu_nghi")
    return out
