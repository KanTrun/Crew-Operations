"""Unit tests for Google Real-Time Index Bridge for Meta Threads."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ca_agents.ag_trend import _scrape_threads_smart
from ca_agents.sources.threads_google_bridge_source import (
    _assess_lifecycle,
    _detect_category,
    parse_google_rss_xml,
    scrape_threads_google_bridge,
)


_MOCK_GOOGLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News - Threads F&amp;B</title>
    <item>
      <title>Trà sữa đậm vị matcha kem béo (@saigon_foodie) on Threads</title>
      <link>https://www.threads.net/@saigon_foodie/post/123456789</link>
      <pubDate>Tue, 01 Sep 2026 03:30:00 GMT</pubDate>
      <description>&lt;p&gt;Cơn sốt matcha kem béo đang bùng nổ ở các quán cà phê Sài Gòn hôm nay.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Tâm sự đi làm quán cafe ca tối (@barista_viet) on Threads</title>
      <link>https://www.threads.net/@barista_viet/post/987654321</link>
      <pubDate>Tue, 01 Sep 2026 02:15:00 GMT</pubDate>
      <description>&lt;p&gt;Drama đi làm ca tối và những vị khách dễ thương.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>
"""


def test_parse_google_rss_xml():
    items = parse_google_rss_xml(_MOCK_GOOGLE_RSS_XML)
    assert len(items) == 2
    
    item1 = items[0]
    assert "Trà sữa đậm vị matcha" in item1["title"]
    assert item1["author"] == "saigon_foodie"
    assert item1["link"] == "https://www.threads.net/@saigon_foodie/post/123456789"
    assert "Cơn sốt matcha kem béo" in item1["snippet"]

    item2 = items[1]
    assert item2["author"] == "barista_viet"
    assert "Drama đi làm ca tối" in item2["snippet"]


def test_detect_category():
    assert _detect_category("Cà phê muối", "Quán cà phê mới mở") == "am_thuc_fnb"
    assert _detect_category("Overthinking", "Meme tâm sự đi làm") == "meme_cau_noi"
    assert _detect_category("Dạo phố", "Cuối tuần ngắm cảnh") == "tam_ly_lifestyle"


def test_assess_lifecycle():
    vong_doi, growth, viral_score, _ = _assess_lifecycle("Matcha cháy hàng", "Món này đang cực hot viral", "")
    assert vong_doi == "dang_dinh"
    assert viral_score >= 90
    assert growth >= 700.0

    vong_doi2, growth2, viral_score2, _ = _assess_lifecycle("Bình yên quán mộc", "Góc nhỏ làm việc nhẹ nhàng", "")
    assert vong_doi2 == "moi_nhu"
    assert viral_score2 < 90


def test_scrape_threads_google_bridge_end_to_end():
    mock_resp = MagicMock()
    mock_resp.read.return_value = _MOCK_GOOGLE_RSS_XML.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        items = scrape_threads_google_bridge(keyword="matcha", count=5)
        assert len(items) == 2
        
        item = items[0]
        assert item.nguon_goc == "threads_vn"
        assert item.loai_xu_huong == "breaking_vn_24h"
        assert item.danh_muc == "am_thuc_fnb"
        assert "THREADS REALTIME" in item.tieu_de
        assert "https://www.threads.net/@saigon_foodie/post/123456789" == item.link_goc
        assert item.is_live_scraped is True
        assert len(item.binh_luan_that_tiktok) > 0


def test_scrape_threads_smart_prioritizes_google_bridge():
    """Khi Google Bridge thành công -> Không gọi Apify để tiết kiệm quota."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = _MOCK_GOOGLE_RSS_XML.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp), \
         patch("ca_agents.sources.threads_apify_source.scrape_threads_apify") as apify_mock:
        items = _scrape_threads_smart(keyword="matcha", count=5, scrape_mode="auto")
        assert len(items) > 0
        assert items[0].nguon_goc == "threads_vn"
        # Apify was NOT called because Google Bridge succeeded (0 cost)
        apify_mock.assert_not_called()


def test_scrape_threads_smart_falls_back_when_google_bridge_fails():
    """Khi Google Bridge lỗi -> Tự động kích hoạt Apify backup."""
    with patch("ca_agents.sources.threads_google_bridge_source.scrape_threads_google_bridge", side_effect=Exception("Network error")), \
         patch("ca_agents.sources.threads_direct_source.scrape_threads_direct", side_effect=Exception("Direct error")), \
         patch("ca_agents.sources.threads_apify_source.scrape_threads_apify") as apify_mock:
        
        apify_mock.return_value = []
        _scrape_threads_smart(keyword="matcha", count=5, scrape_mode="auto")
        apify_mock.assert_called_once()
