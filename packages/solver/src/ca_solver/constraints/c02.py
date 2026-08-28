"""c02 — đủ người theo so_nguoi_toi_thieu + đủ kỹ năng vị trí."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_solver.model import LichInput


def check(data: LichInput) -> list[str]:
    out: list[str] = []
    for ca_id in data.ca_ids:
        nvs = data.phan_cong.get(ca_id, [])
        need_n = data.so_nguoi_toi_thieu.get(ca_id, 1)
        if len(nvs) < need_n:
            out.append(f"c02:{ca_id}:thieu_nguoi:{len(nvs)}<{need_n}")
            continue
        need_skill = data.vi_tri_can.get(ca_id)
        if not need_skill:
            continue
        for nv in nvs:
            if need_skill not in data.ky_nang.get(nv, set()):
                out.append(f"c02:{ca_id}:{nv}:thieu_ky_nang:{need_skill}")
    return out
