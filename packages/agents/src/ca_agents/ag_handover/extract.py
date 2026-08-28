"""AG-HANDOVER — free-text ca handover → SBAR + việc treo. Replay, no LLM."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Handover:
    tinh_hinh: str
    boi_canh: str
    danh_gia: str
    de_nghi: str
    treo: list[str] = field(default_factory=list)
    do_tin_cay: float = 0.82
    nguon: str = "keyword"


def extract(text: str) -> Handover:
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]
    buckets: dict[str, list[str]] = {
        "tinh_hinh": [],
        "boi_canh": [],
        "danh_gia": [],
        "de_nghi": [],
        "treo": [],
    }
    cur = "tinh_hinh"
    for ln in lines:
        low = ln.lower()
        if low.startswith(("tình hình", "tinh hinh", "s:")):
            cur = "tinh_hinh"
            ln = ln.split(":", 1)[-1].strip() or ln
        elif low.startswith(("bối cảnh", "boi canh", "b:")):
            cur = "boi_canh"
            ln = ln.split(":", 1)[-1].strip() or ln
        elif low.startswith(("đánh giá", "danh gia", "a:")):
            cur = "danh_gia"
            ln = ln.split(":", 1)[-1].strip() or ln
        elif low.startswith(("đề nghị", "de nghi", "r:")):
            cur = "de_nghi"
            ln = ln.split(":", 1)[-1].strip() or ln
        elif low.startswith(("treo", "việc treo", "viec treo")):
            cur = "treo"
            ln = ln.split(":", 1)[-1].strip() or ln
        if cur == "treo":
            buckets["treo"].append(ln)
        else:
            buckets[cur].append(ln)
    if not any(buckets[k] for k in ("tinh_hinh", "boi_canh", "danh_gia", "de_nghi")):
        body = " ".join(lines) or text
        return Handover(
            tinh_hinh=body,
            boi_canh="chưa tách được — cần quản lý xác nhận",
            danh_gia="chưa tách được",
            de_nghi="hỏi ca sau xác nhận từng việc treo",
            treo=[],
            do_tin_cay=0.55,
        )
    return Handover(
        tinh_hinh=" ".join(buckets["tinh_hinh"]) or "(trống)",
        boi_canh=" ".join(buckets["boi_canh"]) or "(trống)",
        danh_gia=" ".join(buckets["danh_gia"]) or "(trống)",
        de_nghi=" ".join(buckets["de_nghi"]) or "(trống)",
        treo=buckets["treo"],
    )
