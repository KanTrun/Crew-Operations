"""AG-MSG — 6 intents, two-tier (keyword then live LLM or replay fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ca_agents.llm import complete, parse_json_object

INTENTS = (
    "doi_ca",
    "nhan_ca",
    "bao_tre",
    "cap_nhat_tkb",
    "xin_nghi",
    "khac",
)

_TIER1: list[tuple[str, tuple[str, ...]]] = [
    ("doi_ca", ("đổi ca", "doi ca", "đổi với", "doi voi", "swap")),
    ("nhan_ca", ("nhận ca", "nhan ca", "nhận giúp", "làm hộ", "lam ho")),
    ("bao_tre", ("trễ", "tre ", "muộn", "muon", "đến chậm", "den cham")),
    ("cap_nhat_tkb", ("tkb", "thời khoá", "thoi khoa", "học t", "hoc t", "cập nhật học")),
    ("xin_nghi", ("xin nghỉ", "xin nghi", "nghỉ ca", "nghi ca", "không đi làm", "khong di lam")),
]
_PROMPT = Path(__file__).resolve().parents[1] / "prompts" / "ag_msg" / "0.1.0.md"


@dataclass(frozen=True)
class MsgResult:
    intent: str
    tier: int
    do_tin_cay: float
    rang_buoc: dict[str, str]


def _norm(text: str) -> str:
    return text.lower().strip()


def _fallback(reason: str) -> MsgResult:
    return MsgResult(
        intent="khac",
        tier=2,
        do_tin_cay=0.55,
        rang_buoc={"nguon": reason},
    )


def classify(text: str, *, mode: str = "replay") -> MsgResult:
    t = _norm(text)
    for intent, keys in _TIER1:
        if any(k in t for k in keys):
            return MsgResult(
                intent=intent,
                tier=1,
                do_tin_cay=0.86,
                rang_buoc={"nguon": "keyword"},
            )
    if mode != "live":
        return _fallback("tier2_fallback")

    system = _PROMPT.read_text(encoding="utf-8") if _PROMPT.exists() else (
        'Trả JSON {"intent": một trong doi_ca|nhan_ca|bao_tre|cap_nhat_tkb|xin_nghi|khac}.'
    )
    result = complete(system=system, user=text, task="text:ag_msg", json_mode=True)
    if not result.ok:
        return _fallback(f"llm_fail:{result.reason}")
    parsed = parse_json_object(result.text)
    intent = str((parsed or {}).get("intent") or "").strip()
    if intent not in INTENTS:
        return _fallback("llm_parse_or_label")
    return MsgResult(
        intent=intent,
        tier=2,
        do_tin_cay=0.72,
        rang_buoc={"nguon": f"llm:{result.provider}"},
    )
