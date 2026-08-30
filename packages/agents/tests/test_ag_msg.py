from __future__ import annotations

from ca_agents.ag_msg import INTENTS, classify


def test_six_intents_defined() -> None:
    assert len(INTENTS) == 6


def test_keyword_tier1() -> None:
    assert classify("anh cho em đổi ca chiều").intent == "doi_ca"
    assert classify("em xin nghỉ ca sáng").intent == "xin_nghi"
    assert classify("cho em đổi với bạn chiều nay").intent == "doi_ca"
    assert classify("máy pha kêu lạ").intent == "khac"


def test_nhan_ca_intent() -> None:
    """Phân loại tin nhắn nhận ca với từ khóa 'nhận ca'."""
    res = classify("nhận ca tối giúp bạn")
    assert res.intent == "nhan_ca"
    assert res.tier == 1


def test_bao_tre_intent() -> None:
    """Phân loại tin nhắn báo trễ với từ khóa 'muộn'."""
    res = classify("em đến muộn 15 phút")
    assert res.intent == "bao_tre"
    assert res.tier == 1


def test_cap_nhat_tkb_intent() -> None:
    """Phân loại tin nhắn cập nhật thời khóa biểu với từ khóa 'TKB'."""
    res = classify("cập nhật TKB tuần sau")
    assert res.intent == "cap_nhat_tkb"
    assert res.tier == 1


def test_tier2_fallback() -> None:
    """Tin nhắn không khớp từ khóa rơi về tier 2 fallback với độ tin cậy 0.55."""
    res = classify("thời tiết hôm nay đẹp quá")
    assert res.intent == "khac"
    assert res.tier == 2
    assert res.do_tin_cay == 0.55
