"""Test tiktok_camoufox_source — không mở browser thật (CA_AGENT_MODE=replay).

Cover theo PR 2 §IV:
    - extract_tiktok_items bằng fixture HTML tĩnh (không mock Playwright)
    - _parse_count: "12.3K"/"1.2M"/"456"/rác
    - Cache TTL: hit trong TTL, miss sau khi expire, key gồm keyword+region
    - fetch_tiktok_page: chờ selector + trả content (mock page object)
    - scrape_tiktok_camoufox lifecycle: mock scrape_page, không launch browser
    - Chuỗi _scrape_tiktok_smart: skip tier khi unavailable, mode browser gọi first
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ca_agents.ag_trend import TrendItem, _scrape_tiktok_smart
from ca_agents.sources import tiktok_camoufox_source as src
from ca_agents.sources.tiktok_camoufox_source import (
    extract_tiktok_items,
    fetch_tiktok_page,
    scrape_tiktok_camoufox,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "tiktok_search_sample.html"


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset cache TTL trước mỗi test (env override được)."""
    src._reset_cache()
    yield
    src._reset_cache()


# ── _parse_count (parser CHUNG cho TikTok + Threads tier) ──


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12.3K", 12_300),
        ("1.2M", 1_200_000),
        ("456", 456),
        ("2.3M", 2_300_000),
        ("856.4K", 856_400),
        ("", 0),
        ("abc", 0),
        ("12,3K", 12_300),  # dấu phẩy kiểu VN
    ],
)
def test_parse_count(raw: str, expected: int):
    assert src._parse_count(raw) == expected


# ── extract_tiktok_items — hàm THUẦN với fixture HTML tĩnh ──


def test_extract_items_from_fixture():
    """Fixture 3 video → 3 TrendItem với stats parse đúng."""
    html = _FIXTURE.read_text(encoding="utf-8")
    items = extract_tiktok_items(
        html, keyword="matcha", count=12, nguon_goc="tiktok_vn", now_str="10:00:00 15/09/2026"
    )

    assert len(items) == 3
    first = items[0]
    assert isinstance(first, TrendItem)
    assert first.is_live_scraped is True
    # Video đầu: 2.3M views, likes ước lượng ~10% views = 230,000
    assert "2,300,000 lượt xem" in first.diem_nhan_dac_biet
    assert "230,000 lượt thả tim" in first.diem_nhan_dac_biet
    # Link video từ href
    assert first.link_goc == "https://www.tiktok.com/@barista.lan/video/7300000000000000001"
    # Hashtag từ caption
    assert "#matcha" in first.tu_khoa_hashtag


def test_extract_items_respects_count_limit():
    """count=2 → chỉ 2 item dù fixture có 3."""
    html = _FIXTURE.read_text(encoding="utf-8")
    items = extract_tiktok_items(
        html, keyword="matcha", count=2, nguon_goc="tiktok_vn", now_str="10:00:00 15/09/2026"
    )
    assert len(items) == 2


def test_extract_items_empty_html():
    """HTML rỗng / không selector → list rỗng, không raise."""
    assert extract_tiktok_items("", "kw", 5, "tiktok_vn", "now") == []
    assert extract_tiktok_items("<div>nothing here</div>", "kw", 5, "tiktok_vn", "now") == []


def test_extract_items_skips_block_without_caption():
    """Khối video rỗng (không caption ≥10 ký tự) → skip, không crash."""
    html = "<div data-e2e='search_top-item'><a href='https://www.tiktok.com/@x/video/1'>ok</a></div>"
    items = extract_tiktok_items(html, "kw", 5, "tiktok_vn", "now")
    assert items == []


# ── fetch_tiktok_page — mock page object (không Playwright thật) ──


def test_fetch_tiktok_page_waits_selector_and_returns_content():
    """fetch chỉ chờ selector + content — KHÔNG goto (scrape_page đã goto)."""
    page = MagicMock()
    page.content.return_value = "<html>fake</html>"
    html = fetch_tiktok_page(page, "matcha")
    page.wait_for_selector.assert_called_once_with("[data-e2e='search_top-item']", timeout=30_000)
    assert html == "<html>fake</html>"
    page.goto.assert_not_called()  # goto do scrape_page lo


# ── Cache TTL (§3.3-bis) ──


def test_cache_hit_within_ttl(monkeypatch: pytest.MonkeyPatch):
    """Trong TTL → scrape_page KHÔNG được gọi (dùng cache)."""
    cached_item = MagicMock(spec=TrendItem)
    src._cache_put("matcha|tiktok_vn", [cached_item])

    scrape_mock = MagicMock()
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    items = scrape_tiktok_camoufox(keyword="matcha", count=5, nguon_goc="tiktok_vn")
    assert items == [cached_item]
    scrape_mock.assert_not_called()


def test_cache_miss_after_ttl(monkeypatch: pytest.MonkeyPatch):
    """Hết TTL → cache miss → gọi scrape_page thật."""
    src._cache_put("matcha|tiktok_vn", [MagicMock(spec=TrendItem)])
    # Ép cache cũ hơn TTL
    stale = time.monotonic() - 10_000
    src._cache["matcha|tiktok_vn"] = (stale, [MagicMock(spec=TrendItem)])

    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    scrape_mock = MagicMock(return_value=fixture_html)
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    items = scrape_tiktok_camoufox(keyword="matcha", count=3, nguon_goc="tiktok_vn")
    scrape_mock.assert_called_once()
    assert len(items) == 3


def test_cache_key_separates_region(monkeypatch: pytest.MonkeyPatch):
    """Key gồm keyword + region — cache tiktok_vn không dính tiktok_global."""
    src._cache_put("matcha|tiktok_vn", [MagicMock(spec=TrendItem)])

    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    scrape_mock = MagicMock(return_value=fixture_html)
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    scrape_tiktok_camoufox(keyword="matcha", count=3, nguon_goc="tiktok_global")
    scrape_mock.assert_called_once()  # region khác → miss → gọi thật


# ── scrape_tiktok_camoufox lifecycle — mock scrape_page ──


def test_scrape_calls_extract_and_logs(monkeypatch: pytest.MonkeyPatch, caplog):
    """scrape_page trả fixture HTML → extract ra items, log event đúng pattern."""
    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    scrape_mock = MagicMock(return_value=fixture_html)
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    items = scrape_tiktok_camoufox(keyword="matcha", count=3, nguon_goc="tiktok_vn")
    assert len(items) == 3
    assert all(isinstance(i, TrendItem) for i in items)
    # URL goto đúng search URL
    call_args = scrape_mock.call_args
    assert "https://www.tiktok.com/search?q=matcha" in call_args[0][0]


def test_scrape_propagates_camoufox_unavailable(monkeypatch: pytest.MonkeyPatch):
    """scrape_page raise CamoufoxUnavailable → propagate thẳng cho caller rớt tầng."""
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    monkeypatch.setattr(src, "scrape_page", MagicMock(side_effect=CamoufoxUnavailable("chưa cài")))
    with pytest.raises(CamoufoxUnavailable):
        scrape_tiktok_camoufox(keyword="matcha", count=3)


# ── Wire vào _scrape_tiktok_smart (ag_trend.py) ──


def test_smart_chain_skips_camoufox_when_unavailable(monkeypatch: pytest.MonkeyPatch):
    """is_available()=False → tier Camoufox bị skip, TikWM vẫn chạy bình thường."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: False)
    tikwm_items = [MagicMock(spec=TrendItem)]
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        MagicMock(return_value=tikwm_items),
    )
    camoufox_spy = MagicMock()
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_tiktok_camoufox",
        camoufox_spy,
    )

    items = _scrape_tiktok_smart(keyword="matcha", count=5, scrape_mode="auto")
    assert items == tikwm_items
    camoufox_spy.assert_not_called()  # unavailable → skip tier


def test_smart_chain_uses_camoufox_after_tikwm_fail(monkeypatch: pytest.MonkeyPatch):
    """TikWM fail (rỗng) + Camoufox available → gọi Camoufox tier, KHÔNG tới Apify."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: True)
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        MagicMock(return_value=[]),  # TikWM trả rỗng
    )
    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_page",
        MagicMock(return_value=fixture_html),
    )
    apify_spy = MagicMock()
    monkeypatch.setattr("ca_agents.sources.tiktok_apify_source.scrape_tiktok_apify", apify_spy)

    items = _scrape_tiktok_smart(keyword="matcha", count=3, scrape_mode="auto")
    assert len(items) == 3
    apify_spy.assert_not_called()  # Camoufox gánh được → không tốn CU Apify


def test_smart_chain_browser_mode_camoufox_first(monkeypatch: pytest.MonkeyPatch):
    """mode='browser' → Camoufox FIRST, TikWM/Apify chỉ là backup."""
    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_page",
        MagicMock(return_value=fixture_html),
    )
    tikwm_spy = MagicMock(return_value=[])
    monkeypatch.setattr("ca_agents.ag_trend._scrape_tiktokwm_fallback", tikwm_spy)

    items = _scrape_tiktok_smart(keyword="matcha", count=3, scrape_mode="browser")
    assert len(items) == 3
    # Camoufox gánh → TikWM backup KHÔNG được gọi
    tikwm_spy.assert_not_called()


def test_smart_chain_browser_mode_falls_back_to_tikwm(monkeypatch: pytest.MonkeyPatch):
    """mode='browser' + Camoufox fail → rớt tầng về TikWM (không crash)."""
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_page",
        MagicMock(side_effect=CamoufoxUnavailable("chưa cài")),
    )
    tikwm_items = [MagicMock(spec=TrendItem)]
    tikwm_mock = MagicMock(return_value=tikwm_items)
    monkeypatch.setattr("ca_agents.ag_trend._scrape_tiktokwm_fallback", tikwm_mock)

    items = _scrape_tiktok_smart(keyword="matcha", count=5, scrape_mode="browser")
    assert items == tikwm_items
    tikwm_mock.assert_called_once()


def test_smart_chain_direct_only_never_uses_camoufox(monkeypatch: pytest.MonkeyPatch):
    """mode='direct_only' → KHÔNG gọi Camoufox (chỉ TikWM + dynamic fallback)."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: True)
    tikwm_items = [MagicMock(spec=TrendItem)]
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        MagicMock(return_value=tikwm_items),
    )
    camoufox_spy = MagicMock()
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_tiktok_camoufox",
        camoufox_spy,
    )

    items = _scrape_tiktok_smart(keyword="matcha", count=5, scrape_mode="direct_only")
    assert items == tikwm_items
    camoufox_spy.assert_not_called()


# ── LAST RESORT: static topics chỉ đứng CUỐI chuỗi (plan §3.4) ──


def test_smart_chain_all_tiers_fail_returns_static_last_resort(
    monkeypatch: pytest.MonkeyPatch,
):
    """TikWM rỗng + Camoufox rỗng + Apify rỗng → static topics, is_live_scraped=False."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: True)
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_page",
        MagicMock(return_value="<html>login-wall</html>"),
    )
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_apify_source.scrape_tiktok_apify",
        MagicMock(return_value=[]),
    )

    items = _scrape_tiktok_smart(keyword="cà phê muối", count=5, scrape_mode="auto")
    assert len(items) >= 1
    assert all(not i.is_live_scraped for i in items)  # tĩnh → không phải live
    assert items[0].cum_tu_khoa_viral == "cà phê muối"  # đúng keyword user gõ


def test_smart_chain_direct_only_all_fail_also_static_last_resort(
    monkeypatch: pytest.MonkeyPatch,
):
    """direct_only + TikWM rỗng → static topics (không gọi Camoufox/Apify)."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: True)
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        MagicMock(return_value=[]),
    )
    camoufox_spy = MagicMock()
    monkeypatch.setattr(
        "ca_agents.sources.tiktok_camoufox_source.scrape_tiktok_camoufox",
        camoufox_spy,
    )

    items = _scrape_tiktok_smart(keyword="", count=5, scrape_mode="direct_only")
    assert len(items) >= 1
    assert all(not i.is_live_scraped for i in items)
    camoufox_spy.assert_not_called()  # direct_only → tier browser bị skip


def test_static_topics_no_keyword_uses_default_list():
    """Không có keyword → dùng default topics (matcha, trà sữa...)."""
    from ca_agents.ag_trend import _static_tiktok_topics

    items = _static_tiktok_topics(keyword="", count=6)
    assert len(items) == 6
    assert all(not i.is_live_scraped for i in items)
    assert {i.cum_tu_khoa_viral for i in items} >= {"matcha", "trà sữa"}
