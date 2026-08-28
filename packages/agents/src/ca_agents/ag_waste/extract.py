"""AG-WASTE — cluster waste notes by weekday. No DB writes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass
class WasteHint:
    cau: str
    thu: str
    n: int
    loai: str = "hao_hut"


def cluster(notes: list[tuple[str, str]]) -> list[WasteHint]:
    """notes = (thu, text)."""
    c: Counter[str] = Counter()
    for thu, text in notes:
        if "dư" in text.lower() or "hết" in text.lower() or "hao" in text.lower():
            c[thu] += 1
    out = []
    for thu, n in c.most_common():
        if n >= 2:
            out.append(
                WasteHint(
                    cau=f"Hao hụt lặp lại vào {thu} — xem lại nhập hàng ngày đó",
                    thu=thu,
                    n=n,
                )
            )
    return out
