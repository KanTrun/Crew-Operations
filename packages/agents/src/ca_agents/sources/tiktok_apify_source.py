"""Map Apify clockworks/tiktok-scraper output → list[TrendItem].

Schema input (Apify actor):
    {
        "searchQueries": ["xuhuong"],   # mode=search
        "hashtags": ["fyp"],            # mode=hashtag
        "profiles": ["user"],            # mode=profile
        "maxItems": 12,
        "proxyCountryCode": "VN",
        "downloadVideo": False,
    }

Schema output (mỗi item):
    {
        "id": "7xxxxxxxxxxxxxxxxxxx",        # video id
        "text": "caption ...",
        "createTimeISO": "2026-01-15T10:30:00.000Z",
        "createTime": "1736937000",
        "authorMeta": {
            "id": "...",
            "name": "user_unique_id",
            "nickName": "User Nickname",
            "verified": False,
            "signature": "...",
            "avatar": "https://..."
        },
        "musicMeta": {
            "musicName": "...",
            "musicAuthor": "...",
            "musicOriginal": True
        },
        "webVideoUrl": "https://www.tiktok.com/@user/video/xxx",
        "videoUrl": "https://...cdn.tiktok...",   # chỉ có nếu downloadVideo=true
        "videoMeta": {
            "height": 1920,
            "width": 1080,
            "duration": 15,
            "coverUrl": "https://..."
        },
        "stats": {
            "playCount": 12345,
            "diggCount": 200,
            "shareCount": 50,
            "commentCount": 30,
            "collectCount": 0
        },
        "hashtags": [{"name": "fyp", "id": "..."}],
        "mentions": [{"name": "user", "id": "..."}],
        "comments": []                            # chỉ có nếu input yêu cầu
    }

Public API:
    scrape_tiktok_apify(keyword, count, mode, nguon_goc) -> list[TrendItem]
    Raise ApifyError nếu fail → caller fallback TikWM.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ca_agents.clients.apify_client import run_actor_sync

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

ACTOR_ID = os.getenv("APIFY_TIKTOK_ACTOR_ID", "clockworks/tiktok-scraper")

_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)


def _build_input(keyword: str, count: int, mode: str) -> dict[str, Any]:
    """Build input payload theo schema Apify clockworks/tiktok-scraper."""
    base: dict[str, Any] = {
        "maxItems": count,
        "downloadVideo": False,  # tiết kiệm CU
        "proxyCountryCode": "VN",
    }
    kw = keyword.strip() if keyword else ""
    if mode == "search":
        if kw:
            base["searchQueries"] = [kw]
    elif mode == "hashtag":
        if kw:
            base["hashtags"] = [kw.lstrip("#")]
    elif mode == "profile":
        if kw:
            base["profiles"] = [kw.lstrip("@")]
    return base


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _format_count(n: int) -> str:
    """1234567 → '1,234,567'."""
    return f"{n:,}"


def _format_comments(comments: list[dict]) -> list[str]:
    """Format comments kiểu `@user: "text" (❤️ N tim)`, top 5."""
    out: list[str] = []
    for c in (comments or [])[:5]:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        user = c.get("uniqueId") or c.get("user", {}).get("unique_id") or "user"
        likes = _safe_int(c.get("diggCount", c.get("likes", 0)))
        out.append(f'@{user}: "{text}" (❤️ {likes} tim)')
    return out


def _extract_hashtags(text: str) -> list[str]:
    """Trích hashtag từ caption text."""
    if not text:
        return []
    found = _HASHTAG_RE.findall(text)
    return [f"#{h}" for h in found][:8]


def _map_item(
    item: dict[str, Any],
    idx: int,
    keyword: str,
    nguon_goc: str,
    now_str: str,
) -> TrendItem:
    """Map 1 Apify item → TrendItem."""
    # Lazy import để tránh circular với ag_trend.py
    from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword

    author_meta = item.get("authorMeta") or {}

    author_id = author_meta.get("name", "user")
    nickname = author_meta.get("nickName") or author_id
    video_id = str(item.get("id") or "")
    text = (item.get("text") or "").strip()

    # Apify clockworks trả stats ở ROOT, không phải trong "stats" dict.
    play_count = _safe_int(item.get("playCount"))
    digg_count = _safe_int(item.get("diggCount"))
    comment_count = _safe_int(item.get("commentCount"))
    share_count = _safe_int(item.get("shareCount"))
    collect_count = _safe_int(item.get("collectCount"))

    # URL
    video_url = item.get("webVideoUrl") or f"https://www.tiktok.com/@{author_id}/video/{video_id}"

    # Keyword cho hashtag
    short_kw = keyword.strip() or extract_core_tiktok_keyword(text) or author_id
    clean_tag = re.sub(r"[^a-zA-Z0-9]", "", short_kw.lower())
    tag_url = f"https://www.tiktok.com/tag/{clean_tag}" if clean_tag else video_url

    # Title
    title_prefix = "🎵 [TIKTOK VIRAL]"
    if nguon_goc == "tiktok_global":
        title_prefix = "🌐 [TIKTOK GLOBAL]"
    if not text:
        text = f"Video TikTok về #{short_kw}"
    tieu_de = f"{title_prefix} {text[:65]}..." if len(text) > 65 else f"{title_prefix} {text}"

    # Hashtags
    hashtags = _extract_hashtags(text)
    if not hashtags:
        hashtags = [f"#{clean_tag}", "#xuhuongtiktok"]
    hashtags = list(dict.fromkeys(hashtags))[:6]  # dedupe, top 6

    return TrendItem(
        id=f"apify_tiktok_{idx}_{video_id}",
        tieu_de=tieu_de,
        cum_tu_khoa_viral=short_kw,
        nguon_goc=nguon_goc,
        loai_xu_huong="breaking_vn_24h",
        danh_muc="trao_luu_pop_culture",
        vong_doi="dang_dinh",
        diem_nhan_dac_biet=(
            f"Kênh sáng tạo: @{author_id} ({nickname}). "
            f"Thống kê thật: {_format_count(play_count)} lượt xem | "
            f"{_format_count(digg_count)} lượt thả tim | "
            f"{_format_count(comment_count)} bình luận | "
            f"{_format_count(share_count)} chia sẻ | "
            f"{_format_count(collect_count)} lưu."
        ),
        nguon_goc_chi_tiet=f"Cào qua Apify actor {ACTOR_ID} lúc {now_str}.",
        ngu_canh_su_dung=(
            "Video đang được đẩy trên For You / Hashtag TikTok "
            # Stats raw cho downstream UI xài
            # (extra attribute, không nằm trong dataclass gốc)  f"với {_format_count(play_count)} lượt xem."
        ),
        tam_ly_gioi_tre="Tương tác trực tiếp trên video triệu view.",
        toc_do_tang_truong_24h=max(300.0, 990.0 - (idx * 40)),
        diem_tiem_nang_viral=max(80, 99 - idx),
        du_bao_thoi_gian="Đang phân phối mạnh trên For You Page",
        link_goc=video_url,
        tiktok_url=video_url,
        tiktok_tag_url=tag_url,
        thoi_gian_cao=now_str,
        luot_tiep_can=(f"{_format_count(play_count)} views | {_format_count(digg_count)} tim"),
        trich_doan_noi_dung_that=f"Caption: {text[:200]}",
        binh_luan_that_tiktok=_format_comments(item.get("comments") or []),
        nen_tang_lan_toa=["TikTok VN", "Facebook Reels", "YouTube Shorts"],
        tu_khoa_hashtag=hashtags,
        is_live_scraped=True,
    )


def scrape_tiktok_apify(
    keyword: str = "",
    count: int = 12,
    mode: str = "search",  # "search" | "hashtag" | "profile"
    nguon_goc: str = "tiktok_vn",  # "tiktok_vn" | "tiktok_global"
) -> list[TrendItem]:
    """
    Cào TikTok qua Apify. Raise ApifyError nếu fail → caller fallback.

    Args:
        keyword:  từ khóa / hashtag / username tuỳ mode.
        count:    số video tối đa.
        mode:     search | hashtag | profile.
        nguon_goc: tiktok_vn | tiktok_global.

    Returns:
        list[TrendItem]: tối đa `count` items.
    """
    start = time.monotonic()
    payload = _build_input(keyword, count, mode)
    raw_items = run_actor_sync(ACTOR_ID, payload)

    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    items_out: list[TrendItem] = []
    for idx, v in enumerate(raw_items[:count]):
        try:
            mapped = _map_item(v, idx, keyword, nguon_goc, now_str)
            items_out.append(mapped)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "apify_map_item_skipped idx=%d reason=%s",
                idx,
                f"{type(e).__name__}: {e}",
            )

    logger.info(
        "apify_tiktok_source_ok",
        extra={
            "source": "apify",
            "mode": mode,
            "nguon_goc": nguon_goc,
            "keyword": keyword[:50],
            "items_count": len(items_out),
            "duration_ms": int((time.monotonic() - start) * 1000),
        },
    )
    return items_out
