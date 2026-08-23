"""AG-SOP — answer only from phiếu YAML + approved laws. Else chưa có."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SopAnswer:
    cau_tra_loi: str
    trich_dan: list[str]
    chua_co: bool


def answer(question: str, *, buoc: list[dict[str, Any]], luat: list[dict[str, Any]]) -> SopAnswer:
    q = question.lower()
    hits: list[str] = []
    bits: list[str] = []
    for b in buoc:
        ten = str(b.get("ten") or "")
        ma = str(b.get("ma") or "")
        blob = f"{ma} {ten}".lower()
        if any(tok in blob for tok in q.split() if len(tok) > 3) or (
            "tủ lạnh" in q and "tủ lạnh" in ten.lower()
        ):
            hits.append(f"phieu:{ma}")
            extra = ""
            ng = b.get("nguong") or {}
            if ng:
                extra = f" (ngưỡng {ng.get('min')}–{ng.get('max')})"
            bits.append(f"{ten}{extra}")
        if "nhiệt" in q and "nhiệt" in ten.lower():
            hits.append(f"phieu:{ma}")
            bits.append(ten)
    for law in luat:
        if law.get("trang_thai") != "hieu_luc":
            continue
        cau = str(law.get("cau") or "")
        if any(tok in cau.lower() for tok in q.split() if len(tok) > 3):
            hits.append(f"luat:{law.get('id')}")
            bits.append(cau)
    # unique hits
    seen: list[str] = []
    for h in hits:
        if h not in seen:
            seen.append(h)
    if not seen:
        return SopAnswer(
            cau_tra_loi="Chưa có trong cẩm nang của quán, hãy hỏi quản lý.",
            trich_dan=[],
            chua_co=True,
        )
    return SopAnswer(
        cau_tra_loi=" ".join(dict.fromkeys(bits)),
        trich_dan=seen,
        chua_co=False,
    )
