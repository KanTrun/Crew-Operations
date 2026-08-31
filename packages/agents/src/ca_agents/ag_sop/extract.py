"""AG-SOP — answer only from phiếu YAML + approved laws. Else chưa có."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ca_agents.llm import agent_mode, complete, parse_json_object

_SOP_SYSTEM = """Bạn là trợ lý cẩm nang NHỊP QUÁN.
Chỉ trả lời từ NGỮ CẢNH được cung cấp (bước phiếu + luật hiệu lực).
Trả JSON: {"cau_tra_loi": "...", "trich_dan": ["phieu:ma", "luat:id"], "chua_co": false}
Nếu ngữ cảnh không đủ: {"cau_tra_loi": "Chưa có trong cẩm nang của quán, hãy hỏi quản lý.", "trich_dan": [], "chua_co": true}
Mỗi trich_dan phải trỏ tới mã có trong ngữ cảnh. Cấm bịa quy trình."""

_STOP = frozenset(
    {
        "mấy",
        "giờ",
        "phải",
        "là",
        "được",
        "gì",
        "như",
        "thế",
        "nào",
        "khi",
        "cho",
        "trong",
        "và",
        "có",
        "không",
        "bao",
        "nhiêu",
        "làm",
        "sao",
        "một",
        "các",
        "theo",
        "của",
        "về",
        "với",
        "từ",
        "đến",
        "hay",
        "hoặc",
        "này",
        "đó",
        "để",
        "ra",
        "vào",
        "trên",
        "dưới",
        "đã",
        "sẽ",
        "cần",
        "nên",
        "thì",
        "mà",
        "bị",
        "là",
        "thế",
        "nào",
        "được",
        "không",
    }
)

_PHRASES = (
    "tủ lạnh",
    "tủ đông",
    "vệ sinh",
    "kiểm kê",
    "bàn giao",
    "đóng quán",
    "nhiệt độ",
)


@dataclass
class SopAnswer:
    cau_tra_loi: str
    trich_dan: list[str]
    chua_co: bool
    mode: str = "keyword"
    provider: str = ""
    do_tin: float = 0.0


def _words(text: str) -> list[str]:
    return re.findall(
        r"[\wàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+",
        text.lower(),
    )


def _question_tokens(question: str) -> list[str]:
    return [w for w in _words(question) if len(w) >= 2 and w not in _STOP]


def _unmatched_ratio(q_tokens: list[str], blob_words: set[str]) -> float:
    long_tokens = [t for t in q_tokens if len(t) >= 3]
    if not long_tokens:
        return 0.0
    unmatched = sum(1 for t in long_tokens if t not in blob_words)
    return unmatched / len(long_tokens)


def _score_blob(question: str, q_tokens: list[str], blob: str) -> float:
    if not q_tokens:
        return 0.0
    blob_words = set(_words(blob))
    q_lower = question.lower()
    token_hits = sum(1 for t in q_tokens if t in blob_words)
    ratio = token_hits / len(q_tokens)
    phrase_bonus = sum(0.2 for p in _PHRASES if p in q_lower and p in blob.lower())
    orphan_penalty = _unmatched_ratio(q_tokens, blob_words) * 0.35
    return max(0.0, ratio + phrase_bonus - orphan_penalty)


def _format_buoc(b: dict[str, Any]) -> str:
    ten = str(b.get("ten") or "")
    phieu_ten = str(b.get("phieu_ten") or b.get("phieu") or "quy trình")
    ng = b.get("nguong") or {}
    cau = f"Theo phiếu {phieu_ten}: {ten}."
    if ng and ng.get("min") is not None and ng.get("max") is not None:
        cau += f" Ngưỡng {ng.get('min')}–{ng.get('max')}°C."
    return cau


def _chua_co_answer() -> SopAnswer:
    return SopAnswer(
        cau_tra_loi="Chưa có trong cẩm nang của quán, hãy hỏi quản lý.",
        trich_dan=[],
        chua_co=True,
        mode="keyword",
        provider="",
        do_tin=0.0,
    )


def _build_context(buoc: list[dict[str, Any]], luat: list[dict[str, Any]]) -> tuple[str, set[str]]:
    valid: set[str] = set()
    lines: list[str] = ["=== Bước phiếu ==="]
    for b in buoc:
        ma = str(b.get("ma") or "")
        ten = str(b.get("ten") or "")
        phieu = str(b.get("phieu_ten") or b.get("phieu") or "")
        if ma:
            valid.add(f"phieu:{ma}")
        ng = b.get("nguong") or {}
        extra = f" ngưỡng {ng.get('min')}–{ng.get('max')}" if ng else ""
        prefix = f"[{phieu}] " if phieu else ""
        lines.append(f"- phieu:{ma} | {prefix}{ten}{extra}")
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
    q_tokens = _question_tokens(question)
    best_buoc: tuple[float, dict[str, Any]] | None = None
    best_law: tuple[float, dict[str, Any]] | None = None

    for b in buoc:
        ma = str(b.get("ma") or "")
        ten = str(b.get("ten") or "")
        blob = f"{ma} {ten}"
        score = _score_blob(question, q_tokens, blob)
        if score < 0.45:
            continue
        blob_words = set(_words(blob))
        if _unmatched_ratio(q_tokens, blob_words) >= 0.55 and score < 0.8:
            continue
        if best_buoc is None or score > best_buoc[0]:
            best_buoc = (score, b)

    for law in luat:
        if law.get("trang_thai") != "hieu_luc":
            continue
        cau = str(law.get("cau") or "")
        lid = str(law.get("id") or "")
        blob = f"{lid} {cau}"
        score = _score_blob(question, q_tokens, blob)
        if score < 0.45:
            continue
        blob_words = set(_words(blob))
        if _unmatched_ratio(q_tokens, blob_words) >= 0.55 and score < 0.8:
            continue
        if best_law is None or score > best_law[0]:
            best_law = (score, law)

    if best_buoc is None and best_law is None:
        return _chua_co_answer()

    picks: list[tuple[float, str, str]] = []
    if best_buoc:
        score, b = best_buoc
        picks.append((score, _format_buoc(b), f"phieu:{b.get('ma')}"))
    if best_law:
        score, law = best_law
        cau = str(law.get("cau") or "")
        picks.append((score, cau, f"luat:{law.get('id')}"))
    picks.sort(key=lambda x: x[0], reverse=True)
    top_score, top_cau, top_cite = picks[0]
    trich_dan = [c for _, _, c in picks[:2]]
    seen: list[str] = []
    for c in trich_dan:
        if c not in seen:
            seen.append(c)
    return SopAnswer(
        cau_tra_loi=top_cau,
        trich_dan=seen,
        chua_co=False,
        mode="keyword",
        provider="",
        do_tin=round(min(0.92, top_score), 2),
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
            cau_tra_loi=str(
                data.get("cau_tra_loi") or "Chưa có trong cẩm nang của quán, hãy hỏi quản lý."
            ),
            trich_dan=[],
            chua_co=True,
            mode="live",
            provider=res.provider,
            do_tin=0.0,
        )
    if not trich or not all(t in valid for t in trich):
        return None
    cau = str(data.get("cau_tra_loi") or "").strip()
    if not cau:
        return None
    return SopAnswer(
        cau_tra_loi=cau,
        trich_dan=trich,
        chua_co=False,
        mode="live",
        provider=res.provider,
        do_tin=0.85,
    )


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
    kw = _answer_keyword(question, buoc=buoc, luat=luat)
    if resolved == "live" and not kw.chua_co:
        kw.mode = "keyword"
    return kw
