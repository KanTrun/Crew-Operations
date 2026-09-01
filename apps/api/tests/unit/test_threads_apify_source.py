"""Unit tests cho threads_apify_source.py — mock Apify client & Threads mapping."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from ca_agents.clients.apify_client import ApifyError
from ca_agents.sources.threads_apify_source import (
    _build_input,
    _detect_category,
    _extract_hashtags,
    _format_count,
    _format_replies,
    scrape_threads_apify,
)
from ca_agents.ag_trend import _scrape_threads_smart


def _apify_threads_item(
    post_id: str = "3456789012345678901",
    text: str = "Tâm sự một ngày làm ca sáng tại quán cafe với trà sữa matcha",
    likes: int = 1540,
    replies_count: int = 85,
    reposts: int = 20,
    username: str = "genz_coffee_lover",
    replies: list | None = None,
) -> dict:
    return {
        "id": post_id,
        "text": text,
        "publishedOn": "2026-08-31T10:30:00.000Z",
        "user": {
            "username": username,
            "pk": "123456",
        },
        "url": f"https://www.threads.net/@{username}/post/{post_id}",
        "likeCount": likes,
        "replyCount": replies_count,
        "repostCount": reposts,
        "replies": replies or [
            {"username": "barista_minh", "text": "Trà matcha ngon đỉnh!", "likeCount": 12}
        ],
    }


def test_build_input_search():
    p = _build_input("matcha", 6, "search")
    assert p["searchQueries"] == ["matcha"]
    assert p["maxItems"] == 6
    assert p["proxyCountryCode"] == "VN"


def test_build_input_tag():
    p = _build_input("#caphemuoi", 8, "tag")
    assert p["hashtags"] == ["caphemuoi"]
    assert p["maxItems"] == 8


def test_format_count():
    assert _format_count(450) == "450"
    assert _format_count(1500) == "1.5K"
    assert _format_count(2_400_000) == "2.4M"


def test_extract_hashtags():
    tags = _extract_hashtags("Thử ngay #matchalatte thơm ngon cùng #fnbvietnam nhé!")
    assert tags == ["#matchalatte", "#fnbvietnam"]


def test_detect_category():
    assert _detect_category("Uống cà phê", "Quán cà phê mới mở") == "am_thuc_fnb"
    assert _detect_category("Overthinking", "Meme tâm sự tuổi trẻ") == "meme_cau_noi"
    assert _detect_category("Một ngày bình yên", "Dạo phố cuối tuần") == "tam_ly_lifestyle"


def test_format_replies():
    raw = [
        {"username": "lan", "text": "Đồng cảm quá", "likeCount": 5},
        {"username": "nam", "text": "Quán ở đâu vậy?", "likeCount": 0},
    ]
    formatted = _format_replies(raw)
    assert len(formatted) == 2
    assert '@lan: "Đồng cảm quá" (❤️ 5)' in formatted[0]
    assert '@nam: "Quán ở đâu vậy?"' in formatted[1]


def test_scrape_threads_apify_success():
    mock_data = [
        _apify_threads_item(
            post_id="post_001",
            text="Trào lưu cà phê muối đang hot trở lại ở Sài Gòn #caphemuoi",
            likes=2500,
            replies_count=130,
        )
    ]
    with patch("ca_agents.sources.threads_apify_source.run_actor_sync", return_value=mock_data):
        items = scrape_threads_apify(keyword="cà phê muối", count=5)
        assert len(items) == 1
        item = items[0]
        assert item.nguon_goc == "threads_vn"
        assert item.danh_muc == "am_thuc_fnb"
        assert "THREADS VIRAL" in item.tieu_de
        assert "https://www.threads.net/@genz_coffee_lover/post/post_001" == item.link_goc
        assert "2.5K tim | 130 phản hồi" in item.luot_tiep_can
        assert len(item.binh_luan_that_tiktok) > 0


def test_scrape_threads_smart_fallback_when_apify_fails():
    with patch(
        "ca_agents.sources.threads_direct_source.scrape_threads_direct",
        side_effect=Exception("Direct mạng lỗi"),
    ), patch(
        "ca_agents.sources.threads_apify_source.run_actor_sync",
        side_effect=ApifyError("Apify token hết hạn"),
    ):
        # When both Direct and Apify fail, _scrape_threads_smart must NOT raise, but fallback to RSS gracefully
        items = _scrape_threads_smart(keyword="", count=5)
        assert isinstance(items, list)
        assert len(items) > 0
        assert items[0].nguon_goc == "threads_vn"


def test_scrape_threads_direct_primary():
    from ca_agents.sources.threads_direct_source import scrape_threads_direct

    items = scrape_threads_direct(keyword="matcha", count=4)
    assert len(items) > 0
    item = items[0]
    assert item.nguon_goc == "threads_vn"
    assert "threads.net" in item.link_goc
    assert item.diem_tiem_nang_viral >= 80
    assert item.vong_doi in ("moi_nhu", "dang_dinh")
    assert len(item.binh_luan_that_tiktok) > 0

