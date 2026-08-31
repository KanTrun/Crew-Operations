"""AG-SOP — answer only from phiếu YAML + approved laws. Else chưa có."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ca_agents.llm import agent_mode, complete, parse_json_object

_SOP_SYSTEM = """Bạn là trợ lý cẩm nang NHỊP QUÁN.
Chỉ trả lời từ NGỮ CẢNH được cung cấp (bước phiếu + luật hiệu lực).
Trả JSON: {"cau_tra_loi": "...", "trich_dan": ["phieu:ma", "luat:id"], "chua_co": false}
Nếu ngữ cảnh không đủ: {"cau_tra_loi": "Chưa có trong cẩm nang của quán, hãy hỏi quản lý.", "trich_dan": [], "chua_co": true}
Mỗi trich_dan phải trỏ tới mã có trong ngữ cảnh. Cấm bịa quy trình."""


@dataclass
class SopAnswer:
    cau_tra_loi: str
    trich_dan: list[str]
    chua_co: bool


def _build_context(buoc: list[dict[str, Any]], luat: list[dict[str, Any]]) -> tuple[str, set[str]]:
    valid: set[str] = set()
    lines: list[str] = ["=== Bước phiếu ==="]
    for b in buoc:
        ma = str(b.get("ma") or "")
        ten = str(b.get("ten") or "")
        if ma:
            valid.add(f"phieu:{ma}")
        ng = b.get("nguong") or {}
        extra = f" ngưỡng {ng.get('min')}–{ng.get('max')}" if ng else ""
        lines.append(f"- phieu:{ma} | {ten}{extra}")
    lines.append("=== Luật hiệu lực ===")
    for law in luat:
        if law.get("trang_thai") != "hieu_luc":
            continue
        lid = str(law.get("id") or "")
        cau = str(law.get("cau") or "")
        if lid:
            valid.add(f"luat:{lid}")
        lines.append(f"- luat:{lid} | {cau}")
    return "\n".join(lines), valid


def _answer_keyword(question: str, *, buoc: list[dict[str, Any]], luat: list[dict[str, Any]]) -> SopAnswer:
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


def _answer_live(
    question: str,
    *,
    buoc: list[dict[str, Any]],
    luat: list[dict[str, Any]],
) -> SopAnswer | None:
    ctx, valid = _build_context(buoc, luat)
    user = json.dumps({"cau_hoi": question, "ngu_canh": ctx}, ensure_ascii=False)
    res = complete(system=_SOP_SYSTEM, user=user, task="ag_sop", json_mode=True)
    if not res.ok:
        return None
    data = parse_json_object(res.text)
    if not data:
        return None
    chua_co = bool(data.get("chua_co"))
    trich = [str(x) for x in (data.get("trich_dan") or []) if str(x)]
    if chua_co:
        return SopAnswer(
            cau_tra_loi=str(data.get("cau_tra_loi") or "Chưa có trong cẩm nang của quán, hãy hỏi quản lý."),
            trich_dan=[],
            chua_co=True,
        )
    if not trich or not all(t in valid for t in trich):
        return None
    cau = str(data.get("cau_tra_loi") or "").strip()
    if not cau:
        return None
    return SopAnswer(cau_tra_loi=cau, trich_dan=trich, chua_co=False)


def answer(
    question: str,
    *,
    buoc: list[dict[str, Any]],
    luat: list[dict[str, Any]],
    mode: str | None = None,
) -> SopAnswer:
    resolved = (mode or agent_mode() or "replay").strip().lower()
    if resolved == "live":
        live = _answer_live(question, buoc=buoc, luat=luat)
        if live:
            return live
    return _answer_keyword(question, buoc=buoc, luat=luat)
