"""Test threads_trending_source — kiểm thử cào bảng Trending Now trên Threads.

Cover các ca kiểm thử:
    - extract_threads_trending_items từ fixture HTML tĩnh (DOM structure)
    - extract_threads_trending_items từ embedded JSON GraphQL relay
    - Giới hạn count
    - HTML rỗng / không hợp lệ không gây crash
    - Phát hiện login-wall khi chưa cấu hình phiên đăng nhập
    - Quản lý Cache TTL
    - Truyền user_data_dir xuống scrape_page
    - Đấu nối ag_trend._scrape_threads_smart khi keyword rỗng
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ca_agents.ag_trend import TrendItem, _scrape_threads_smart
from ca_agents.clients.camoufox_client import CamoufoxUnavailable
from ca_agents.sources import threads_trending_source as src
from ca_agents.sources.threads_trending_source import (
    extract_threads_trending_items,
    fetch_threads_trending_page,
    scrape_threads_trending,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "threads_trending_sample.html"


@pytest.fixture(autouse=True)
def _reset_trending_cache():
    """Reset cache trước mỗi test."""
    src._reset_cache()
    yield
    src._reset_cache()


def test_extract_trending_items_from_fixture():
    """Trích xuất 4 chủ đề từ fixture mẫu mô phỏng giao diện Trending thực tế."""
    html = _FIXTURE.read_text(encoding="utf-8")
    items = extract_threads_trending_items(
        html, count=10, nguon_goc="threads_vn", now_str="10:00:00 15/09/2026"
    )

    assert len(items) == 4
    first = items[0]
    assert isinstance(first, TrendItem)
    assert first.is_live_scraped is True
    assert "Trường Giang" in first.tieu_de
    assert "9K posts" in first.luot_tiep_can or "9,000" in first.luot_tiep_can
    assert first.vong_doi == "moi_nhu"
    assert "threads.net/search?q=" in first.link_goc

    # Item thứ 3: Grab và ShopeeFood với 81K posts -> dang_dinh (>= 10K)
    grab_item = items[2]
    assert "Grab và ShopeeFood" in grab_item.tieu_de
    assert grab_item.vong_doi == "dang_dinh"


def test_extract_trending_respects_count_limit():
    """count=2 -> chỉ trả về đúng 2 item dù fixture có 4."""
    html = _FIXTURE.read_text(encoding="utf-8")
    items = extract_threads_trending_items(html, count=2, nguon_goc="threads_vn")
    assert len(items) == 2


def test_extract_trending_empty_html():
    """HTML rỗng -> trả list rỗng, không raise ngoại lệ."""
    assert extract_threads_trending_items("") == []
    assert extract_threads_trending_items("<div>no trending content</div>") == []


def test_extract_trending_from_embedded_json():
    """Trích xuất thành công khi trang nhúng payload JSON GraphQL."""
    json_html = """
    <html>
    <head>
      <script type="application/json">
      {
        "trending_topics": [
          {
            "title": "Cà phê muối chú Long",
            "subtitle": "Trào lưu cà phê muối lan rộng khắp các tỉnh thành",
            "post_count": 15000,
            "thumbnail_url": "https://example.com/muoi.jpg"
          },
          {
            "title": "Trà sữa đất nung",
            "subtitle": "Món trà giữ nhiệt cho mùa đông",
            "post_count": "5.2K",
            "thumbnail_url": ""
          }
        ]
      }
      </script>
    </head>
    <body></body>
    </html>
    """
    items = extract_threads_trending_items(json_html, count=5)
    assert len(items) == 2
    assert "Cà phê muối chú Long" in items[0].tieu_de
    assert items[0].vong_doi == "dang_dinh"
    assert "Trà sữa đất nung" in items[1].tieu_de
    assert items[1].vong_doi == "moi_nhu"


def test_fetch_trending_page_login_wall():
    """Nếu trang search hiển thị form login mà không có nội dung trending -> raise CamoufoxUnavailable."""
    mock_page = MagicMock()
    mock_page.content.return_value = '<html><body><a href="/login">Log in</a><div>Chưa đăng nhập</div></body></html>'
    mock_page.query_selector.return_value = MagicMock()  # login link exists

    with pytest.raises(CamoufoxUnavailable, match="Yêu cầu đăng nhập"):
        fetch_threads_trending_page(mock_page)


def test_fetch_trending_page_timeout():
    """Nếu selector main không xuất hiện -> raise CamoufoxUnavailable."""
    mock_page = MagicMock()
    mock_page.wait_for_selector.side_effect = TimeoutError("main not found")

    with pytest.raises(CamoufoxUnavailable, match="không tải được vùng nội dung chính"):
        fetch_threads_trending_page(mock_page)


def test_cache_lifecycle():
    """Kiểm tra lưu cache và hit cache."""
    key = src._cache_key("threads_vn")
    assert src._cache_get(key) is None

    fake_item = TrendItem(
        id="th_1",
        tieu_de="Test Trend",
        cum_tu_khoa_viral="Test",
        nguon_goc="threads_vn",
        loai_xu_huong="breaking_vn_24h",
        danh_muc="am_thuc_fnb",
        vong_doi="moi_nhu",
        diem_nhan_dac_biet="",
        nguon_goc_chi_tiet="",
        ngu_canh_su_dung="",
        tam_ly_gioi_tre="",
        toc_do_tang_truong_24h=50.0,
        diem_tiem_nang_viral=90,
        du_bao_thoi_gian="24h",
        link_goc="https://threads.net",
        tiktok_url="",
        tiktok_tag_url="",
        thoi_gian_cao="now",
        luot_tiep_can="1K posts",
        trich_doan_noi_dung_that="",
        binh_luan_that_tiktok=[],
        nen_tang_lan_toa=[],
        tu_khoa_hashtag=[],
    )

    src._cache_put(key, [fake_item])
    cached = src._cache_get(key)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].tieu_de == "Test Trend"


@patch("ca_agents.sources.threads_trending_source.scrape_page")
def test_scrape_threads_trending_forwards_user_data_dir(mock_scrape_page):
    """Xác nhận user_data_dir được truyền đúng xuống camoufox_client.scrape_page."""
    mock_scrape_page.return_value = _FIXTURE.read_text(encoding="utf-8")

    items = scrape_threads_trending(user_data_dir="/custom/profile", count=3)
    assert len(items) == 3

    assert mock_scrape_page.called
    kwargs = mock_scrape_page.call_args.kwargs
    assert kwargs.get("user_data_dir") == "/custom/profile"


@patch("ca_agents.sources.threads_trending_source.scrape_threads_trending")
@patch("ca_agents.clients.camoufox_client.is_available", return_value=True)
def test_ag_trend_integration_empty_keyword_calls_trending(mock_avail, mock_trending):
    """Khi keyword rỗng trong browser mode, ag_trend ưu tiên gọi scrape_threads_trending."""
    fake_item = TrendItem(
        id="th_trend_1",
        tieu_de="Trending Topic",
        cum_tu_khoa_viral="Topic",
        nguon_goc="threads_vn",
        loai_xu_huong="breaking_vn_24h",
        danh_muc="am_thuc_fnb",
        vong_doi="dang_dinh",
        diem_nhan_dac_biet="",
        nguon_goc_chi_tiet="",
        ngu_canh_su_dung="",
        tam_ly_gioi_tre="",
        toc_do_tang_truong_24h=80.0,
        diem_tiem_nang_viral=95,
        du_bao_thoi_gian="24h",
        link_goc="https://threads.net",
        tiktok_url="",
        tiktok_tag_url="",
        thoi_gian_cao="now",
        luot_tiep_can="50K posts",
        trich_doan_noi_dung_that="",
        binh_luan_that_tiktok=[],
        nen_tang_lan_toa=[],
        tu_khoa_hashtag=[],
    )
    mock_trending.return_value = [fake_item]

    items = _scrape_threads_smart(keyword="", count=5, nguon_goc="threads_vn", scrape_mode="browser")
    assert len(items) == 1
    assert items[0].tieu_de == "Trending Topic"
    assert mock_trending.called
