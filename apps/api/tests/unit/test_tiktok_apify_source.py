"""Unit tests cho tiktok_apify_source.py — mock Apify client."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from ca_agents.clients.apify_client import ApifyError
from ca_agents.sources.tiktok_apify_source import (
    _build_input,
    _extract_hashtags,
    _format_comments,
    _format_count,
    scrape_tiktok_apify,
)


# ─── Fixtures ───────────────────────────────────────────────────────


def _apify_item(
    video_id: str = "7000000000000000001",
    text: str = "Hello world",
    play: int = 12345,
    digg: int = 200,
    comment: int = 30,
    author: str = "test_user",
    nickname: str = "Test User",
    comments: list | None = None,
) -> dict:
    return {
        "id": video_id,
        "text": text,
        "createTimeISO": "2026-08-30T10:30:00.000Z",
        "authorMeta": {
            "name": author,
            "nickName": nickname,
            "verified": False,
        },
        "webVideoUrl": f"https://www.tiktok.com/@{author}/video/{video_id}",
        "videoMeta": {"height": 1920, "width": 1080, "duration": 15},
        # Apify clockworks trả stats ở ROOT
        "playCount": play,
        "diggCount": digg,
        "shareCount": 10,
        "commentCount": comment,
        "collectCount": 0,
        "comments": comments or [],
    }


# ─── Pure-function tests ────────────────────────────────────────────


def test_build_input_search():
    p = _build_input("xuhuong", 5, "search")
    assert p["searchQueries"] == ["xuhuong"]
    assert p["maxItems"] == 5
    assert p["downloadVideo"] is False
    assert p["proxyCountryCode"] == "VN"


def test_build_input_hashtag_strips_hash():
    p = _build_input("#fyp", 10, "hashtag")
    assert p["hashtags"] == ["fyp"]


def test_build_input_profile_strips_at():
    p = _build_input("@user", 10, "profile")
    assert p["profiles"] == ["user"]


def test_build_input_empty_keyword_search():
    p = _build_input("", 10, "search")
    assert "searchQueries" not in p


def test_format_count():
    assert _format_count(0) == "0"
    assert _format_count(1234) == "1,234"
    assert _format_count(1234567) == "1,234,567"


def test_extract_hashtags_basic():
    assert _extract_hashtags("hello #fyp #xuhuong world") == ["#fyp", "#xuhuong"]


def test_extract_hashtags_empty():
    assert _extract_hashtags("no tags here") == []


def test_extract_hashtags_limits_to_8():
    text = " ".join(f"#tag{i}" for i in range(20))
    assert len(_extract_hashtags(text)) == 8


def test_format_comments_top_5():
    comments = [
        {"uniqueId": f"user{i}", "text": f"comment {i}", "diggCount": i}
        for i in range(7)
    ]
    out = _format_comments(comments)
    assert len(out) == 5
    assert out[0] == '@user0: "comment 0" (❤️ 0 tim)'
    assert out[4] == '@user4: "comment 4" (❤️ 4 tim)'


def test_format_comments_skips_empty_text():
    comments = [
        {"uniqueId": "u1", "text": "real comment"},
        {"uniqueId": "u2", "text": ""},
        {"uniqueId": "u3", "text": "   "},
    ]
    out = _format_comments(comments)
    assert len(out) == 1
    assert "real comment" in out[0]


def test_format_comments_empty_input():
    assert _format_comments([]) == []


# ─── Integration with mocked Apify client ───────────────────────────


def test_scrape_happy_path_returns_items():
    items_in = [_apify_item(video_id=f"v{i}", text=f"caption {i}") for i in range(5)]
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=items_in,
    ):
        out = scrape_tiktok_apify(keyword="xuhuong", count=5)
    assert len(out) == 5
    for idx, t in enumerate(out):
        assert t.id.startswith(f"apify_tiktok_{idx}_")
        assert t.nguon_goc == "tiktok_vn"
        assert "xuhuong" in t.tieu_de.lower() or "tiktok viral" in t.tieu_de.lower()


def test_scrape_apify_error_propagates():
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        side_effect=ApifyError("empty"),
    ):
        with pytest.raises(ApifyError, match="empty"):
            scrape_tiktok_apify(keyword="x")


def test_scrape_text_truncated_to_65_chars():
    long_text = "a" * 200
    items_in = [_apify_item(text=long_text)]
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=items_in,
    ):
        out = scrape_tiktok_apify(keyword="k", count=1)
    # Prefix + 65 chars + "..."
    assert len(out) == 1
    tieu_de = out[0].tieu_de
    assert tieu_de.endswith("...")
    # 65 ký tự a + "..."
    assert "a" * 65 in tieu_de


def test_scrape_missing_stats_uses_zero():
    """Khi item thiếu stats → các field hiển thị 0."""
    item = _apify_item(play=0, digg=0)
    # Xóa hết stats fields
    for k in ["playCount", "diggCount", "shareCount", "commentCount", "collectCount"]:
        item.pop(k, None)
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=[item],
    ):
        out = scrape_tiktok_apify(keyword="k", count=1)
    assert "0 views" in out[0].luot_tiep_can
    assert "0 tim" in out[0].luot_tiep_can


def test_scrape_root_level_stats():
    """Apify clockworks trả stats ở ROOT, không phải stats.*."""
    item = _apify_item(play=100000, digg=500, comment=42)
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=[item],
    ):
        out = scrape_tiktok_apify(keyword="k", count=1)
    assert "100,000 views" in out[0].luot_tiep_can
    assert "500 tim" in out[0].luot_tiep_can
    assert "42 bình luận" in out[0].diem_nhan_dac_biet


def test_scrape_nguon_goc_global_param():
    items_in = [_apify_item()]
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=items_in,
    ):
        out = scrape_tiktok_apify(keyword="trend", count=1, nguon_goc="tiktok_global")
    assert out[0].nguon_goc == "tiktok_global"
    assert "GLOBAL" in out[0].tieu_de


def test_scrape_comments_format_in_trend_item():
    items_in = [
        _apify_item(
            comments=[
                {"uniqueId": "fan1", "text": "great video", "diggCount": 100},
                {"uniqueId": "fan2", "text": "love it", "diggCount": 50},
            ],
        )
    ]
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=items_in,
    ):
        out = scrape_tiktok_apify(keyword="k", count=1)
    assert len(out[0].binh_luan_that_tiktok) == 2
    assert "@fan1" in out[0].binh_luan_that_tiktok[0]


def test_scrape_url_fallback_when_missing():
    item = _apify_item(video_id="abc123")
    del item["webVideoUrl"]
    with patch(
        "ca_agents.sources.tiktok_apify_source.run_actor_sync",
        return_value=[item],
    ):
        out = scrape_tiktok_apify(keyword="k", count=1)
    assert "abc123" in out[0].tiktok_url
    assert "tiktok.com" in out[0].tiktok_url