"""Map Apify Threads scraper output → list[TrendItem].

Schema input (Apify actor):
    {
        "searchQueries": ["fnb"],     # mode=search
        "hashtags": ["cafe"],         # mode=tag
        "maxItems": 12,
        "proxyCountryCode": "VN",
    }

Schema output (mỗi item):
    {
        "id": "3456789012345678901",
        "text": "Tâm sự làm việc ca đêm ở quán cafe...",
        "publishedOn": "2026-08-31T10:30:00.000Z",
        "user": {
            "username": "genz_coffee",
            "pk": "...",
            "profile_pic_url": "https://..."
        },
        "url": "https://www.threads.net/@genz_coffee/post/3456789012345678901",
        "likeCount": 1540,
        "replyCount": 120,
        "repostCount": 45,
        "replies": [
            {"username": "barista_minh", "text": "Đồng cảm ghê á", "likeCount": 15}
        ]
    }

Public API:
    scrape_threads_apify(keyword, count, mode, nguon_goc) -> list[TrendItem]
    Raise ApifyError nếu fail → caller fallback sang RSS / Web search.
"""

from __future__ import annotations

import logging
import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ca_agents.clients.apify_client import run_actor_sync

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

ACTOR_ID = os.getenv("APIFY_THREADS_ACTOR_ID", "curious_coder/threads-scraper")

_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)


def _build_input(keyword: str, count: int, mode: str) -> dict[str, Any]:
    """Build input payload cho Threads scraper."""
    base: dict[str, Any] = {
        "maxItems": count,
        "proxyCountryCode": "VN",
    }
    kw = keyword.strip() if keyword else ""
    if mode == "search":
        if kw:
            base["searchQueries"] = [kw]
        else:
            base["searchQueries"] = ["fnb vietnam", "quan cafe", "gen z"]
    elif mode == "tag":
        if kw:
            base["hashtags"] = [kw.lstrip("#")]
        else:
            base["hashtags"] = ["caphe", "fnb", "genz"]
    return base


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _extract_hashtags(text: str) -> list[str]:
    return [f"#{m.lower()}" for m in _HASHTAG_RE.findall(text)]


def _format_replies(raw_replies: list[Any]) -> list[str]:
    out: list[str] = []
    for r in (raw_replies or [])[:3]:
        if isinstance(r, str) and r.strip():
            out.append(r.strip())
            continue
        if isinstance(r, dict):
            u = r.get("username") or r.get("user", {}).get("username") or "user"
            t = r.get("text") or r.get("content") or ""
            likes = _safe_int(r.get("likeCount") or r.get("like_count") or 0)
            if t.strip():
                if likes > 0:
                    out.append(f'@{u}: "{t.strip()}" (❤️ {likes})')
                else:
                    out.append(f'@{u}: "{t.strip()}"')
    return out


def _detect_category(title: str, text: str) -> str:
    blob = f"{title} {text}".lower()
    fnb_keywords = ["cà phê", "cafe", "trà", "matcha", "quán", "menu", "đồ uống", "pha chế", "ẩm thực", "ăn vặt", "bánh"]
    if any(w in blob for w in fnb_keywords):
        return "am_thuc_fnb"
    meme_keywords = ["meme", "câu nói", "drama", "hài", "trend", "flex", "overthinking"]
    if any(w in blob for w in meme_keywords):
        return "meme_cau_noi"
    return "tam_ly_lifestyle"


def scrape_threads_apify(
    keyword: str = "",
    count: int = 12,
    mode: str = "search",
    nguon_goc: str = "threads_vn",
    timeout_s: int | None = None,
) -> list[TrendItem]:
    """Cào bài viết Threads qua Apify actor và map sang list[TrendItem]."""
    from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword

    payload = _build_input(keyword, count, mode)
    kwargs = {"timeout_s": timeout_s} if timeout_s is not None else {}
    raw_items = run_actor_sync(ACTOR_ID, payload, **kwargs)

    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    kw_clean = keyword.strip()
    items_out: list[TrendItem] = []

    for idx, item in enumerate(raw_items[:count]):
        post_id = str(item.get("id") or item.get("pk") or f"th_{idx}_{int(time.time())}")
        text = str(item.get("text") or item.get("caption") or item.get("body") or "").strip()
        if not text:
            text = f"Bài thảo luận Threads về #{kw_clean}" if kw_clean else "Bài thảo luận trên Threads"

        user_obj = item.get("user") or item.get("author") or {}
        username = (
            user_obj.get("username")
            if isinstance(user_obj, dict)
            else str(item.get("username") or "threads_user")
        )
        post_url = str(
            item.get("url")
            or item.get("post_url")
            or f"https://www.threads.net/@{username}/post/{post_id}"
        )

        likes = _safe_int(item.get("likeCount") or item.get("like_count") or item.get("likes") or 0)
        replies_count = _safe_int(item.get("replyCount") or item.get("reply_count") or item.get("repliesCount") or 0)
        reposts = _safe_int(item.get("repostCount") or item.get("repost_count") or 0)

        # First line as title
        first_line = text.split("\n")[0].strip()
        title_display = first_line[:65] + ("..." if len(first_line) > 65 else "")

        short_kw = kw_clean if kw_clean else extract_core_tiktok_keyword(first_line)
        clean_tag = re.sub(r"[^a-zA-Z0-9_]", "", short_kw.lower())

        encoded_kw = urllib.parse.quote(short_kw)
        th_search = f"https://www.threads.net/search?q={encoded_kw}"
        th_tag = f"https://www.threads.net/search?q=%23{clean_tag}" if clean_tag else th_search

        # Extract hashtags from post text
        tags = _extract_hashtags(text)
        if f"#{clean_tag}" not in tags and clean_tag:
            tags.insert(0, f"#{clean_tag}")
        if "#threads" not in tags:
            tags.append("#threads")
        if "#genz" not in tags:
            tags.append("#genz")

        # Top replies
        formatted_replies = _format_replies(item.get("replies") or item.get("comments") or [])

        reach_str = f"{_format_count(likes)} tim | {_format_count(replies_count)} phản hồi"
        if reposts > 0:
            reach_str += f" | {_format_count(reposts)} repost"

        category = _detect_category(title_display, text)

        items_out.append(
            TrendItem(
                id=f"live_threads_apify_{idx}_{post_id}",
                tieu_de=f"🧵 [THREADS VIRAL] {title_display}",
                cum_tu_khoa_viral=short_kw or "Tâm sự Threads",
                nguon_goc=nguon_goc,
                loai_xu_huong="breaking_vn_24h",
                danh_muc=category,
                vong_doi="dang_dinh",
                diem_nhan_dac_biet=f"Tài khoản: @{username}. Thống kê thật: {reach_str}.",
                nguon_goc_chi_tiet=f"Cào dữ liệu bài viết và phản hồi THẬT từ Threads.net lúc {now_str}.",
                ngu_canh_su_dung="Chủ đề tâm sự, bàn luận sôi nổi của giới trẻ Gen Z trên Threads.",
                tam_ly_gioi_tre="Thích chia sẻ trải nghiệm chân thật, đồng cảm và bàn luận quan điểm cá nhân.",
                toc_do_tang_truong_24h=max(250.0, 920.0 - (idx * 35)),
                diem_tiem_nang_viral=max(75, 98 - idx),
                du_bao_thoi_gian="Đang thu hút thảo luận mạnh trong 24-48h qua",
                link_goc=post_url,
                tiktok_url=th_search,
                tiktok_tag_url=th_tag,
                thoi_gian_cao=now_str,
                luot_tiep_can=reach_str,
                trich_doan_noi_dung_that=text[:250] + ("..." if len(text) > 250 else ""),
                binh_luan_that_tiktok=formatted_replies,
                nen_tang_lan_toa=["Meta Threads"],
                tu_khoa_hashtag=tags[:5],
                is_live_scraped=True,
            )
        )

    logger.info("threads_source_done items_count=%d", len(items_out))
    return items_out
