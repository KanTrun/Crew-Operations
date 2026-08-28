"""Fairness debt 4 axes — minimize maximum debt (ADR-005 / hồ sơ §8.2)."""

from __future__ import annotations

from copy import deepcopy

AXES = ("cuoi_tuan", "dem", "gio", "vun")


def zero_debt(nv_ids: list[str]) -> dict[str, dict[str, float]]:
    return {nid: {a: 0.0 for a in AXES} for nid in nv_ids}


def update_debt_from_assignment(
    debt: dict[str, dict[str, float]],
    phan_cong: dict[str, list[str]],
    ca_meta: dict[str, dict[str, str]],
) -> dict[str, dict[str, float]]:
    out = deepcopy(debt)
    for ca_id, nvs in phan_cong.items():
        m = ca_meta.get(ca_id, {})
        thu = m.get("thu", "")
        khung = m.get("khung", "")
        bat = m.get("bat_dau", "00:00")
        ket = m.get("ket_thuc", "00:00")
        h0, m0 = map(int, bat.split(":"))
        h1, m1 = map(int, ket.split(":"))
        hours = (h1 * 60 + m1 - h0 * 60 - m0) / 60.0
        weekend = thu in {"T7", "CN"}
        night = khung == "toi" or h0 >= 17
        for nv in nvs:
            bal = out.setdefault(nv, {a: 0.0 for a in AXES})
            if weekend:
                bal["cuoi_tuan"] += 1.0
            if night:
                bal["dem"] += 1.0
            bal["gio"] += hours
            # ca vụn: short shift < 5h
            if hours < 5:
                bal["vun"] += 1.0
    return out


def max_debt(debt: dict[str, dict[str, float]]) -> float:
    mx = 0.0
    for bal in debt.values():
        for a in AXES:
            mx = max(mx, float(bal.get(a, 0)))
    return mx


def debt_spread(debt: dict[str, dict[str, float]]) -> float:
    """max - min of per-person total debt (sum of axes)."""
    totals = [sum(bal.get(a, 0) for a in AXES) for bal in debt.values()]
    if not totals:
        return 0.0
    return max(totals) - min(totals)
