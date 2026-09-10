"""Test threads_camoufox_source — không mở browser thật (CA_AGENT_MODE=replay).

Cover theo PR 3 §IV:
    - extract_threads_items bằng fixture HTML tĩnh (không mock Playwright)
    - Tái dùng _detect_category/_assess_trend_lifecycle từ threads_direct_source
    - _is_login_wall: URL redirect + HTML chỉ có nút login
    - fetch_threads_page: chờ selector + trả content (mock page object)
    - Cache TTL: hit trong TTL, miss sau khi expire, key gồm keyword+region
    - scrape_threads_camoufox lifecycle: mock scrape_page, login-wall raise
    - Chuỗi _scrape_threads_smart: skip tier khi unavailable, mode browser gọi first
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ca_agents.ag_trend import TrendItem, _scrape_threads_smart
from ca_agents.sources import threads_camoufox_source as src
from ca_agents.sources.threads_camoufox_source import (
    extract_threads_items,
    fetch_threads_page,
    scrape_threads_camoufox,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "threads_search_sample.html"


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset cache TTL trước mỗi test (env override được)."""
    src._reset_cache()
    yield
    src._reset_cache()


# ── extract_threads_items — hàm THUẦN với fixture HTML tĩnh ──


def test_extract_items_from_fixture():
    """Fixture 3 post → 3 TrendItem với stats parse đúng + category từ helper chung."""
    html = _FIXTURE.read_text(encoding="utf-8")
    items = extract_threads_items(
        html, keyword="matcha", count=12, nguon_goc="threads_vn", now_str="10:00:00 15/09/2026"
    )

    assert len(items) == 3
    first = items[0]
    assert isinstance(first, TrendItem)
    assert first.is_live_scraped is True
    # Post đầu: 2.4K likes, 185 replies → "đang đỉnh cao" (likes >= 1000)
    assert "2,400 tim" in first.diem_nhan_dac_biet
    assert "185 phản hồi" in first.diem_nhan_dac_biet
    assert first.vong_doi == "dang_dinh"
    # Link post từ href
    assert first.link_goc == "https://www.threads.net/@saigon_coffee_guide/post/Cx1a2b3c4d5"
    # Category từ _detect_category (matcha → am_thuc_fnb)
    assert first.danh_muc == "am_thuc_fnb"


def test_extract_items_respects_count_limit():
    """count=2 → chỉ 2 item dù fixture có 3."""
    html = _FIXTURE.read_text(encoding="utf-8")
    items = extract_threads_items(
        html, keyword="matcha", count=2, nguon_goc="threads_vn", now_str="10:00:00 15/09/2026"
    )
    assert len(items) == 2


def test_extract_items_empty_html():
    """HTML rỗng / không selector → list rỗng, không raise."""
    assert extract_threads_items("", "kw", 5, "threads_vn", "now") == []
    assert extract_threads_items("<div>nothing here</div>", "kw", 5, "threads_vn", "now") == []


def test_extract_items_skips_block_without_text():
    """Khối post rỗng (text < 30 ký tự) → skip, không crash."""
    html = '<div data-e2e="search-result-post"><a href="/@x/post/1">ok</a></div>'
    items = extract_threads_items(html, "kw", 5, "threads_vn", "now")
    assert items == []


def test_extract_reuses_lifecycle_helper():
    """Post ít tương tác (likes < 1000) → 'moi_nhu' từ _assess_trend_lifecycle."""
    html = (
        '<div data-e2e="search-result-post">'
        "<a href='/@user/post/Ab1'>Cà phê quán mới mở đẹp lung linh ghé ngay kẻo lỡ</a>"
        "<div>150 12</div></div>"
    )
    items = extract_threads_items(html, "cafe", 5, "threads_vn", "now")
    assert len(items) == 1
    assert items[0].vong_doi == "moi_nhu"


# ── _is_login_wall (plan §3.4) ──


def test_login_wall_detected_by_url():
    """URL redirect về /login → login-wall."""
    assert src._is_login_wall("<html>whatever</html>", "https://www.threads.net/login") is True


def test_login_wall_detected_by_html():
    """HTML không có post + chỉ có nút Log in → login-wall."""
    html = "<html><body><button>Log in</button></body></html>"
    assert src._is_login_wall(html, "https://www.threads.net/search?q=cafe") is True


def test_no_login_wall_when_posts_present():
    """HTML có post thật → KHÔNG phải login-wall."""
    html = _FIXTURE.read_text(encoding="utf-8")
    assert src._is_login_wall(html, "https://www.threads.net/search?q=cafe") is False


# ── fetch_threads_page — mock page object (không Playwright thật) ──


def test_fetch_threads_page_waits_selector_and_returns_content():
    """fetch chỉ chờ selector + content — KHÔNG goto (scrape_page đã goto)."""
    page = MagicMock()
    page.content.return_value = "<html>fake</html>"
    page.query_selector.return_value = None  # không có login-link → không grace-wait
    html = fetch_threads_page(page, "cafe")
    page.wait_for_selector.assert_called_once_with(
        "[data-e2e='search-result-post'], a[href*='/login']", timeout=30_000
    )
    assert html == "<html>fake</html>"
    page.goto.assert_not_called()  # goto do scrape_page lo


def test_fetch_threads_page_fast_fails_on_soft_login_wall():
    """Login-wall mềm: login-link xuất hiện, post không render sau grace-wait
    → raise CamoufoxUnavailable NGAY (~3s) thay vì chờ đủ 30s timeout."""
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    page = MagicMock()
    # wait_for_selector lần 1 (post HOẶC login) thành công; lần 2 (grace-wait
    # post thật, timeout=3s) raise timeout → wall xác nhận.
    page.query_selector.return_value = MagicMock()  # login-link có mặt

    def raise_timeout(selector, timeout):
        if "search-result-post" in selector and timeout == 3_000:
            raise RuntimeError("Timeout 3000ms exceeded")
        return None

    page.wait_for_selector.side_effect = raise_timeout

    with pytest.raises(CamoufoxUnavailable, match="login-wall"):
        fetch_threads_page(page, "cafe")


def test_fetch_threads_page_login_link_but_post_renders_later():
    """Login-link có mặt nhưng post render sau grace-wait → KHÔNG phải wall,
    trả content bình thường (tránh false-positive khi SPA lazy-render)."""
    page = MagicMock()
    page.query_selector.return_value = MagicMock()  # login-link có mặt
    page.wait_for_selector.return_value = None  # mọi wait đều thành công
    page.content.return_value = "<html>posts</html>"

    html = fetch_threads_page(page, "cafe")
    assert html == "<html>posts</html>"


# ── Cache TTL (§3.3-bis) ──


def test_cache_hit_within_ttl(monkeypatch: pytest.MonkeyPatch):
    """Trong TTL → scrape_page KHÔNG được gọi (dùng cache)."""
    cached_item = MagicMock(spec=TrendItem)
    src._cache_put("threads:matcha|threads_vn", [cached_item])

    scrape_mock = MagicMock()
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    items = scrape_threads_camoufox(keyword="matcha", count=5, nguon_goc="threads_vn")
    assert items == [cached_item]
    scrape_mock.assert_not_called()


def test_cache_miss_after_ttl(monkeypatch: pytest.MonkeyPatch):
    """Hết TTL → cache miss → gọi scrape_page thật."""
    src._cache_put("threads:matcha|threads_vn", [MagicMock(spec=TrendItem)])
    # Ép cache cũ hơn TTL
    stale = time.monotonic() - 10_000
    src._cache["threads:matcha|threads_vn"] = (stale, [MagicMock(spec=TrendItem)])

    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    scrape_mock = MagicMock(return_value=fixture_html)
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    items = scrape_threads_camoufox(keyword="matcha", count=3, nguon_goc="threads_vn")
    scrape_mock.assert_called_once()
    assert len(items) == 3


def test_cache_key_separates_from_tiktok(monkeypatch: pytest.MonkeyPatch):
    """Key threads: prefix riêng — không đụng cache TikTok cùng keyword."""
    # Cache TikTok (khác module) không ảnh hưởng; key threads riêng.
    from ca_agents.sources import tiktok_camoufox_source as tt_src

    tt_src._cache_put("matcha|tiktok_vn", [MagicMock(spec=TrendItem)])

    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    scrape_mock = MagicMock(return_value=fixture_html)
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    scrape_threads_camoufox(keyword="matcha", count=3, nguon_goc="threads_vn")
    scrape_mock.assert_called_once()  # threads cache trống → gọi thật


# ── scrape_threads_camoufox lifecycle — mock scrape_page ──


def test_scrape_calls_extract_and_logs(monkeypatch: pytest.MonkeyPatch):
    """scrape_page trả fixture HTML → extract ra items, URL goto đúng search URL."""
    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    scrape_mock = MagicMock(return_value=fixture_html)
    monkeypatch.setattr(src, "scrape_page", scrape_mock)

    items = scrape_threads_camoufox(keyword="matcha", count=3, nguon_goc="threads_vn")
    assert len(items) == 3
    assert all(isinstance(i, TrendItem) for i in items)
    call_args = scrape_mock.call_args
    assert "https://www.threads.net/search?q=matcha" in call_args[0][0]
    assert "serp_type=default" in call_args[0][0]


def test_scrape_propagates_camoufox_unavailable(monkeypatch: pytest.MonkeyPatch):
    """scrape_page raise CamoufoxUnavailable → propagate thẳng cho caller rớt tầng."""
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    monkeypatch.setattr(src, "scrape_page", MagicMock(side_effect=CamoufoxUnavailable("chưa cài")))
    with pytest.raises(CamoufoxUnavailable):
        scrape_threads_camoufox(keyword="matcha", count=3)


def test_login_wall_raises_unavailable(monkeypatch: pytest.MonkeyPatch):
    """Login-wall → CamoufoxUnavailable cho lần gọi đó, rớt tầng NGAY (plan §3.4)."""
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    def fake_scrape_page(url: str, extractor, timeout_s: int = 45):
        page = MagicMock()
        page.url = "https://www.threads.net/login"
        page.content.return_value = "<html><button>Log in</button></html>"
        # wait_for_selector sẽ timeout trên trang login — mock để không chờ thật.
        page.wait_for_selector = MagicMock()
        page.query_selector.return_value = None
        return extractor(page)

    monkeypatch.setattr(src, "scrape_page", fake_scrape_page)

    with pytest.raises(CamoufoxUnavailable, match="login-wall"):
        scrape_threads_camoufox(keyword="matcha", count=3)


# ── Wire vào _scrape_threads_smart (ag_trend.py) ──


def test_smart_chain_skips_camoufox_when_unavailable(monkeypatch: pytest.MonkeyPatch):
    """is_available()=False → tier Camoufox bị skip, chuỗi cũ vẫn chạy."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: False)
    bridge_items = [MagicMock(spec=TrendItem)]
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        MagicMock(return_value=bridge_items),
    )
    camoufox_spy = MagicMock()
    monkeypatch.setattr(
        "ca_agents.sources.threads_camoufox_source.scrape_threads_camoufox",
        camoufox_spy,
    )

    items = _scrape_threads_smart(keyword="matcha", count=5, scrape_mode="auto")
    assert items == bridge_items
    camoufox_spy.assert_not_called()  # unavailable → skip tier


def test_smart_chain_uses_camoufox_after_direct_fail(monkeypatch: pytest.MonkeyPatch):
    """Bridge + Direct fail (rỗng) + Camoufox available → Camoufox tier, KHÔNG tới Apify."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: True)
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.sources.threads_direct_source.scrape_threads_direct",
        MagicMock(return_value=[]),
    )
    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "ca_agents.sources.threads_camoufox_source.scrape_page",
        MagicMock(return_value=fixture_html),
    )
    apify_spy = MagicMock()
    monkeypatch.setattr("ca_agents.sources.threads_apify_source.scrape_threads_apify", apify_spy)

    items = _scrape_threads_smart(keyword="matcha", count=3, scrape_mode="auto")
    assert len(items) == 3
    apify_spy.assert_not_called()  # Camoufox gánh được → không tốn CU Apify


def test_smart_chain_browser_mode_camoufox_first(monkeypatch: pytest.MonkeyPatch):
    """mode='browser' → Camoufox FIRST, Bridge/Direct chỉ là backup."""
    fixture_html = _FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "ca_agents.sources.threads_camoufox_source.scrape_page",
        MagicMock(return_value=fixture_html),
    )
    bridge_spy = MagicMock(return_value=[])
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        bridge_spy,
    )

    items = _scrape_threads_smart(keyword="matcha", count=3, scrape_mode="browser")
    assert len(items) == 3
    # Camoufox gánh → Bridge backup KHÔNG được gọi
    bridge_spy.assert_not_called()


def test_smart_chain_browser_mode_falls_back_to_bridge(monkeypatch: pytest.MonkeyPatch):
    """mode='browser' + Camoufox fail → rớt tầng về Bridge (không crash)."""
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    monkeypatch.setattr(
        "ca_agents.sources.threads_camoufox_source.scrape_page",
        MagicMock(side_effect=CamoufoxUnavailable("chưa cài")),
    )
    bridge_items = [MagicMock(spec=TrendItem)]
    bridge_mock = MagicMock(return_value=bridge_items)
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        bridge_mock,
    )

    items = _scrape_threads_smart(keyword="matcha", count=5, scrape_mode="browser")
    assert items == bridge_items
    bridge_mock.assert_called_once()


def test_smart_chain_direct_only_never_uses_camoufox(monkeypatch: pytest.MonkeyPatch):
    """mode='direct_only' → KHÔNG gọi Camoufox tier (khóa cả browser lẫn Apify)."""
    monkeypatch.setattr("ca_agents.clients.camoufox_client.is_available", lambda: True)
    direct_items = [MagicMock(spec=TrendItem)]
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.sources.threads_direct_source.scrape_threads_direct",
        MagicMock(return_value=direct_items),
    )
    camoufox_spy = MagicMock()
    monkeypatch.setattr(
        "ca_agents.sources.threads_camoufox_source.scrape_threads_camoufox",
        camoufox_spy,
    )

    items = _scrape_threads_smart(keyword="matcha", count=5, scrape_mode="direct_only")
    assert items == direct_items
    camoufox_spy.assert_not_called()


# ── No-hardcoded-fallback (plan §3.4 — fix fake-data tier-blocking) ──


def test_google_bridge_returns_empty_when_rss_empty(monkeypatch: pytest.MonkeyPatch):
    """Google News RSS rỗng → trả [] (KHÔNG curated hardcode giả mạo data thật)."""
    from ca_agents.sources import threads_google_bridge_source as bridge_src

    monkeypatch.setattr(
        bridge_src,
        "parse_google_rss_xml",
        MagicMock(return_value=[]),
    )
    items = bridge_src.scrape_threads_google_bridge(keyword="cà phê", count=5)
    assert items == []
    # Không item nào được gắn is_live_scraped=True từ data giả
    assert all(not getattr(it, "is_live_scraped", False) for it in items)


def test_direct_jina_returns_empty_when_fetch_fails(monkeypatch: pytest.MonkeyPatch):
    """Jina 403/fail → trả [] để chuỗi rớt tầng Camoufox/Apify (KHÔNG curated_hot_threads)."""
    from ca_agents.sources import threads_direct_source as direct_src

    monkeypatch.setattr(
        "urllib.request.urlopen",
        MagicMock(side_effect=RuntimeError("HTTP Error 403: Forbidden")),
    )
    items = direct_src.scrape_threads_direct(keyword="cà phê", count=5)
    assert items == []


def test_smart_chain_all_tiers_empty_falls_to_rss(monkeypatch: pytest.MonkeyPatch):
    """Bridge + Direct + Camoufox + Apify đều rỗng → tầng cuối RSS Kênh14 (data thật)."""
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.sources.threads_direct_source.scrape_threads_direct",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.clients.camoufox_client.is_available",
        lambda: False,
    )
    rss_items = [MagicMock(spec=TrendItem)]
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_genz_media_vn",
        MagicMock(return_value=rss_items),
    )

    items = _scrape_threads_smart(keyword="cà phê", count=5, scrape_mode="auto")
    assert items == rss_items  # rớt tầng tới RSS thật, không phải []


def test_smart_chain_returns_empty_when_all_real_sources_fail(monkeypatch: pytest.MonkeyPatch):
    """Mọi tầng thật fail (kể cả RSS) → trả [] trung thực, KHÔNG giả mạo data."""
    monkeypatch.setattr(
        "ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.sources.threads_direct_source.scrape_threads_direct",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "ca_agents.clients.camoufox_client.is_available",
        lambda: False,
    )
    monkeypatch.setattr(
        "ca_agents.ag_trend._scrape_genz_media_vn",
        MagicMock(return_value=[]),
    )

    items = _scrape_threads_smart(keyword="xyz-khong-ton-tai", count=5, scrape_mode="auto")
    assert items == []  # trung thực: không data giả lấp đầy
