"""Inject luật hiệu lực (Cẩm nang bước 7) vào tham số CP-SAT."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ca_solver.model import LichInput


def apply_luat(data: LichInput, laws: list[dict[str, Any]]) -> tuple[LichInput, list[str]]:
    """Bump ``so_nguoi_toi_thieu`` theo ``tham_so_loi`` / ``dieu_kien`` của luật hiệu lực."""
    so_nguoi = dict(data.so_nguoi_toi_thieu)
    applied: list[str] = []
    for law in laws:
        if law.get("trang_thai") != "hieu_luc":
            continue
        cond = law.get("tham_so_loi") or law.get("dieu_kien") or {}
        thu = cond.get("thu")
        khung = cond.get("khung")
        vi_tri = cond.get("vi_tri")
        need = cond.get("so_nguoi")
        if need is None:
            continue
        need_i = int(need)
        for ca_id, meta in data.ca_meta.items():
            if thu and meta.get("thu") != thu:
                continue
            if khung and meta.get("khung") != khung:
                continue
            if vi_tri and data.vi_tri_can.get(ca_id) != vi_tri:
                continue
            prev = so_nguoi.get(ca_id, 1)
            if prev < need_i:
                so_nguoi[ca_id] = need_i
                applied.append(f"{law.get('id', '?')}:{ca_id}:{prev}->{need_i}")
    if not applied:
        return data, applied
    return replace(data, so_nguoi_toi_thieu=so_nguoi), applied
