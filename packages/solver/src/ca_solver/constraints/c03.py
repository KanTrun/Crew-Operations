"""c03 — một người không ở hai ca cùng lúc."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_solver.model import LichInput


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def check(data: LichInput) -> list[str]:
    by_nv: dict[str, list[str]] = defaultdict(list)
    for ca_id, nvs in data.phan_cong.items():
        for nv in nvs:
            by_nv[nv].append(ca_id)
    out: list[str] = []
    for nv, cas in by_nv.items():
        for i, a in enumerate(cas):
            ma = data.ca_meta.get(a)
            if not ma or "bat_dau" not in ma or "ket_thuc" not in ma:
                continue
            for b in cas[i + 1 :]:
                mb = data.ca_meta.get(b)
                if not mb or ma.get("thu") != mb.get("thu"):
                    continue
                if "bat_dau" not in mb or "ket_thuc" not in mb:
                    continue
                if _to_min(ma["bat_dau"]) < _to_min(mb["ket_thuc"]) and _to_min(
                    mb["bat_dau"]
                ) < _to_min(ma["ket_thuc"]):
                    out.append(f"c03:{nv}:{a}:{b}:trung_ca")
    return out
