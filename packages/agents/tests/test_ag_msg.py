from __future__ import annotations

from ca_agents.ag_msg import INTENTS, classify
from ca_agents.llm import LlmResult


def test_six_intents_defined() -> None:
    assert len(INTENTS) == 6


def test_keyword_tier1() -> None:
    assert classify("anh cho em đổi ca chiều").intent == "doi_ca"
    assert classify("em xin nghỉ ca sáng").intent == "xin_nghi"
    assert classify("cho em đổi với bạn chiều nay").intent == "doi_ca"
    assert classify("máy pha kêu lạ").intent == "khac"


def test_live_tier2_uses_llm_label(monkeypatch: object) -> None:
    def fake_complete(**_k: object) -> LlmResult:
        return LlmResult(
            ok=True,
            text='{"intent":"bao_tre"}',
            provider="groq",
            reason="ok",
        )

    monkeypatch.setattr("ca_agents.ag_msg.extract.complete", fake_complete)  # type: ignore[attr-defined]
    r = classify("em tới sau một lúc", mode="live")
    assert r.intent == "bao_tre"
    assert r.tier == 2
    assert r.rang_buoc["nguon"] == "llm:groq"


def test_live_tier2_invalid_label_fail_closed(monkeypatch: object) -> None:
    def fake_complete(**_k: object) -> LlmResult:
        return LlmResult(ok=True, text='{"intent":"hack_luong"}', provider="groq", reason="ok")

    monkeypatch.setattr("ca_agents.ag_msg.extract.complete", fake_complete)  # type: ignore[attr-defined]
    r = classify("em tới sau một lúc", mode="live")
    assert r.intent == "khac"
    assert r.do_tin_cay < 0.7

