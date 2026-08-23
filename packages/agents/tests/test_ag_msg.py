from __future__ import annotations

from ca_agents.ag_msg import INTENTS, classify


def test_six_intents_defined() -> None:
    assert len(INTENTS) == 6


def test_keyword_tier1() -> None:
    assert classify("anh cho em đổi ca chiều").intent == "doi_ca"
    assert classify("em xin nghỉ ca sáng").intent == "xin_nghi"
    assert classify("cho em đổi với bạn chiều nay").intent == "doi_ca"
    assert classify("máy pha kêu lạ").intent == "khac"
