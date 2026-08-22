"""AG-MSG — 6 intents, two-tier (keyword then replay/overlap)."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class MsgResult:
    intent: str
    tier: int
    do_tin_cay: float
    rang_buoc: dict[str, str]


def _norm(text: str) -> str:
    return text.lower().strip()


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
    # Tier 2: replay overlap — still no live LLM
    _ = mode
    return MsgResult(
        intent="khac",
        tier=2,
        do_tin_cay=0.55,
        rang_buoc={"nguon": "tier2_fallback"},
    )
