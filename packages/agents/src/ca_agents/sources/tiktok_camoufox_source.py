"""Cào TikTok search bằng Camoufox (browser thật chống-detect) → list[TrendItem].

Tier browser-thật miễn phí, chèn GIỮA TikWM và Apify trong chuỗi
`_scrape_tiktok_smart` (ag_trend.py). Không tốn CU Apify, render được JS
của SPA TikTok search, fingerprint spoof ở mức C++/Rust khó bị chặn hơn
urllib + UA hard-code.

Thiết kế tách bạch (plan §3.3):
    - fetch_tiktok_page(page, keyword)  — chờ SPA render (goto do scrape_page lo),
                                          trả HTML của trang hiện tại.
    - extract_tiktok_items(html, ...)   — hàm THUẦN, test bằng fixture HTML tĩnh,
                                          không phụ thuộc Playwright.
    - scrape_tiktok_camoufox(...)       — orchestrate qua camoufox_client.scrape_page
                                          + cache TTL CA_CAMOUFOX_CACHE_TTL_S.

`_parse_count` là parser "12.3K"/"1.2M" CHUNG — threads_camoufox_source (PR 3)
import từ đây, không viết logic parse riêng cho từng tier (plan §3.3).

Public API:
    scrape_tiktok_camoufox(keyword, count, nguon_goc) -> list[TrendItem]
    Raise CamoufoxUnavailable nếu chưa cài/fetch/thiếu system deps → caller rớt tầng.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ca_agents.clients.camoufox_client import scrape_page

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

# Selector khối video trên TikTok search SPA (data-e2e ổn định hơn class CSS).
_VIDEO_SELECTOR = "[data-e2e='search_video-item']"  # cho wait_for_selector (Playwright)
_VIDEO_ATTR = "data-e2e='search_video-item'"  # cho split HTML (không có bracket)
_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)
# TikTok hiển thị stats dạng "12.3K", "1.2M", "456" — parse về int.
_COUNT_RE = re.compile(r"^([\d.,]+)\s*([KMB]?)$", re.IGNORECASE)

# ── Cache in-memory TTL riêng (plan §3.3-bis: 10 phút, tách khỏi TTL TikWM 5 phút) ──
_DEFAULT_CACHE_TTL_S = 600
_cache: dict[str, tuple[float, list[TrendItem]]] = {}


def _get_cache_ttl_s() -> int:
    try:
        return max(60, int(os.getenv("CA_CAMOUFOX_CACHE_TTL_S", str(_DEFAULT_CACHE_TTL_S))))
    except ValueError:
        return _DEFAULT_CACHE_TTL_S


def _cache_key(keyword: str, nguon_goc: str) -> str:
    """Key gồm keyword + region (nguon_goc) — plan §3.3."""
    return f"{(keyword or '').strip().lower()}|{nguon_goc}"


def _cache_get(key: str) -> list[TrendItem] | None:
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is None:
        return None
    cached_at, items = hit
    if now - cached_at > _get_cache_ttl_s():
        _cache.pop(key, None)
        return None
    return items


def _cache_put(key: str, items: list[TrendItem]) -> None:
    _cache[key] = (time.monotonic(), items)


def _reset_cache() -> None:
    """Reset cache (chỉ dùng trong test)."""
    _cache.clear()


def _parse_count(raw: str) -> int:
    """'12.3K' → 12300, '1.2M' → 1200000, '456' → 456. Trả 0 nếu không parse được.

    Parser CHUNG cho các tier Camoufox (TikTok + Threads) — plan §3.3.
    """
    m = _COUNT_RE.match((raw or "").strip())
    if not m:
        return 0
    num_str = m.group(1).replace(",", ".")
    try:
        num = float(num_str)
    except ValueError:
        return 0
    mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[m.group(2).upper()]
    return int(num * mult)


def _format_count(n: int) -> str:
    """1234567 → '1,234,567' (thống nhất với tiktok_apify_source)."""
    return f"{n:,}"


def _extract_hashtags(text: str) -> list[str]:
    """Trích hashtag từ caption (thống nhất với tiktok_apify_source)."""
    if not text:
        return []
    return [f"#{h}" for h in _HASHTAG_RE.findall(text)][:8]


def fetch_tiktok_page(page: Any, keyword: str) -> str:
    """Chờ SPA TikTok search render xong danh sách video, trả HTML trang.

    KHÔNG goto ở đây — `scrape_page(url, extractor)` đã goto tới search URL
    trước khi gọi hàm này (tránh goto 2 lần). Chỉ lo phần chờ render.
    """
    # Chờ SPA render xong danh sách video (timeout do scrape_page quản).
    page.wait_for_selector(_VIDEO_SELECTOR, timeout=30_000)
    content: str = page.content()
    return content


def extract_tiktok_items(
    html: str,
    keyword: str,
    count: int,
    nguon_goc: str,
    now_str: str,
) -> list[TrendItem]:
    """Hàm THUẦN: parse HTML TikTok search → list[TrendItem].

    Không phụ thuộc Playwright — test bằng fixture HTML tĩnh. Khi TikTok đổi
    DOM, chỉ cần cập nhật fixture + hàm này, không đụng browser lifecycle.
    """

    items_out: list[TrendItem] = []
    # Split theo khối video — mỗi khối chứa 1 video + stats.
    blocks = html.split(_VIDEO_ATTR)
    for idx, block in enumerate(blocks[1:]):  # blocks[0] là phần trước video đầu
        if len(items_out) >= count:
            break
        try:
            item = _map_block(block, idx, keyword, nguon_goc, now_str)
            if item is not None:
                items_out.append(item)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "camoufox_tiktok_map_skipped idx=%d reason=%s",
                idx,
                f"{type(e).__name__}: {e}",
            )
    return items_out


def _map_block(
    block_html: str,
    idx: int,
    keyword: str,
    nguon_goc: str,
    now_str: str,
) -> TrendItem | None:
    """Map 1 khối HTML video → TrendItem. Trả None nếu khối rỗng/lỗi parse."""
    from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword

    # Caption: text dài nhất trong khối (giữa các thẻ a href chứa /video/).
    video_link = ""
    m = re.search(r'href="(/@[\w\.\-]+/video/\d+)"', block_html)
    if m:
        video_link = f"https://www.tiktok.com{m.group(1)}"
    author_m = re.search(r"/@([\w\.\-]+)/video/", video_link or "")
    author_id = author_m.group(1) if author_m else "user"

    # Text hiển thị: strip thẻ HTML, lấy đoạn text dài nhất (> 20 ký tự).
    text_no_tags = re.sub(r"<[^>]+>", " ", block_html)
    text_no_tags = re.sub(r"\s+", " ", text_no_tags).strip()
    # Caption thường nằm trước stats — lấy 220 ký tự đầu làm caption thô.
    caption_raw = text_no_tags[:220].strip()
    if len(caption_raw) < 20:
        return None

    # Stats: pattern "số" lặp lại sau caption — parse các số dạng 12.3K/1.2M.
    stat_nums = re.findall(r"(\d[\d.,]*\s*[KMB]?)\b", text_no_tags)
    # TikTok search hiển thị: views (video), likes, comments, shares, saves.
    parsed = [_parse_count(s) for s in stat_nums[:5]]
    play_count = parsed[0] if parsed else 0
    digg_count = parsed[1] if len(parsed) > 1 else 0
    comment_count = parsed[2] if len(parsed) > 2 else 0
    share_count = parsed[3] if len(parsed) > 3 else 0

    short_kw = keyword.strip() or extract_core_tiktok_keyword(caption_raw) or author_id
    clean_tag = re.sub(r"[^a-zA-Z0-9]", "", short_kw.lower())
    tag_url = f"https://www.tiktok.com/tag/{clean_tag}" if clean_tag else video_link

    title_prefix = "🎵 [TIKTOK VIRAL]"
    if nguon_goc == "tiktok_global":
        title_prefix = "🌐 [TIKTOK GLOBAL]"
    tieu_de = (
        f"{title_prefix} {caption_raw[:65]}..."
        if len(caption_raw) > 65
        else f"{title_prefix} {caption_raw}"
    )

    hashtags = _extract_hashtags(caption_raw)
    if not hashtags:
        hashtags = [f"#{clean_tag}", "#xuhuongtiktok"]
    hashtags = list(dict.fromkeys(hashtags))[:6]

    return TrendItem(
        id=f"camoufox_tiktok_{idx}_{clean_tag or idx}",
        tieu_de=tieu_de,
        cum_tu_khoa_viral=short_kw,
        nguon_goc=nguon_goc,
        loai_xu_huong="breaking_vn_24h",
        danh_muc="trao_luu_pop_culture",
        vong_doi="dang_dinh",
        diem_nhan_dac_biet=(
            f"Kênh sáng tạo: @{author_id}. "
            f"Thống kê thật: {_format_count(play_count)} lượt xem | "
            f"{_format_count(digg_count)} lượt thả tim | "
            f"{_format_count(comment_count)} bình luận | "
            f"{_format_count(share_count)} chia sẻ."
        ),
        nguon_goc_chi_tiet=f"Cào qua Camoufox browser thật lúc {now_str}.",
        ngu_canh_su_dung="Video đang được đẩy trên For You / Hashtag TikTok.",
        tam_ly_gioi_tre="Tương tác trực tiếp trên video triệu view.",
        toc_do_tang_truong_24h=max(300.0, 990.0 - (idx * 40)),
        diem_tiem_nang_viral=max(80, 99 - idx),
        du_bao_thoi_gian="Đang phân phối mạnh trên For You Page",
        link_goc=video_link or f"https://www.tiktok.com/search?q={keyword}",
        tiktok_url=video_link or f"https://www.tiktok.com/search?q={keyword}",
        tiktok_tag_url=tag_url,
        thoi_gian_cao=now_str,
        luot_tiep_can=f"{_format_count(play_count)} views | {_format_count(digg_count)} tim",
        trich_doan_noi_dung_that=f"Caption: {caption_raw[:200]}",
        binh_luan_that_tiktok=[],
        nen_tang_lan_toa=["TikTok Việt Nam"],
        tu_khoa_hashtag=hashtags,
        is_live_scraped=True,
    )


def scrape_tiktok_camoufox(
    keyword: str = "",
    count: int = 12,
    nguon_goc: str = "tiktok_vn",
) -> list[TrendItem]:
    """Cào TikTok search qua Camoufox. Raise CamoufoxUnavailable nếu chưa cài.

    Được gọi trong chuỗi `_scrape_tiktok_smart` giữa TikWM và Apify.
    Cache TTL riêng CA_CAMOUFOX_CACHE_TTL_S (mặc định 10 phút, plan §3.3-bis).
    """
    start = time.monotonic()
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    key = _cache_key(keyword, nguon_goc)
    cached = _cache_get(key)
    if cached is not None:
        logger.info(
            "tiktok_source_camoufox_cache_hit",
            extra={
                "source": "camoufox",
                "keyword": keyword[:50],
                "items_count": len(cached),
                "duration_ms": int((time.monotonic() - start) * 1000),
            },
        )
        return cached[:count]

    kw = keyword.strip() or "xuhuong"
    from urllib.parse import quote

    url = f"https://www.tiktok.com/search?q={quote(kw)}"
    html = scrape_page(url, lambda page: fetch_tiktok_page(page, keyword))
    items = extract_tiktok_items(html, keyword, count, nguon_goc, now_str)
    if items:
        _cache_put(key, items)

    logger.info(
        "tiktok_source_camoufox",
        extra={
            "source": "camoufox",
            "nguon_goc": nguon_goc,
            "keyword": keyword[:50],
            "items_count": len(items),
            "duration_ms": int((time.monotonic() - start) * 1000),
        },
    )
    return items
