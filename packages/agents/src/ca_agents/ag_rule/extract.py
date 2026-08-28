"""AG-RULE — one Vietnamese law sentence from a mined pattern. No DB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RuleDraft:
    cau: str
    loai: str
    dieu_kien: dict[str, Any]
    bang_chung: list[str]
    do_tin_cay: float


def propose(mau: dict[str, Any]) -> RuleDraft | None:
    if int(mau.get("n") or 0) < 3:
        return None
    return RuleDraft(
        cau="Thứ Bảy ca chiều cần 3 người pha chế, không phải 2",
        loai=str(mau.get("loai_luat") or "nhu_cau_ca"),
        dieu_kien={"thu": "T7", "khung": "chieu", "vi_tri": "pha_che", "so_nguoi": 3},
        bang_chung=list(mau.get("bang_chung") or [])[:4],
        do_tin_cay=0.8,
    )
