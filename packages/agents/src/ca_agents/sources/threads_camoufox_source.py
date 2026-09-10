"""Cào Threads search bằng Camoufox (browser thật chống-detect) → list[TrendItem].

Tier browser-thật miễn phí, chèn GIỮA Jina direct và Apify trong chuỗi
`_scrape_threads_smart` (ag_trend.py). Threads public search render được
không cần login — Camoufox vượt checkpoint Meta tốt hơn urllib + UA hard-code.

Thiết kế tách bạch (plan §3.4, nhất quán §3.3):
    - fetch_threads_page(page, keyword)  — chờ SPA render, trả HTML trang.
    - extract_threads_items(html, ...)    — hàm THUẦN, test bằng fixture HTML tĩnh.
    - scrape_threads_camoufox(...)        — orchestrate qua camoufox_client.scrape_page
                                             + cache TTL CA_CAMOUFOX_CACHE_TTL_S.

Tái dùng từ source có sẵn (KHÔNG copy code — plan §3.4):
    - `_detect_category`, `_assess_trend_lifecycle` từ threads_direct_source.
    - `_parse_count` (parser "12.3K"/"1.2M" CHUNG) từ tiktok_camoufox_source.

Login-wall (plan §3.4): nếu Threads redirect về màn login → coi như
`CamoufoxUnavailable` cho lần gọi đó, rớt tầng NGAY, không cố đăng nhập
hay vượt qua (đúng ranh giới phạm vi cào plan §2.3).

Public API:
    scrape_threads_camoufox(keyword, count, nguon_goc) -> list[TrendItem]
    Raise CamoufoxUnavailable nếu chưa cài/fetch/thiếu system deps/login-wall
    → caller rớt tầng.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ca_agents.clients.camoufox_client import scrape_page
from ca_agents.sources.threads_direct_source import _assess_trend_lifecycle, _detect_category
from ca_agents.sources.tiktok_camoufox_source import _parse_count

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

# Selector khối post trên Threads search SPA (data-e2e ổn định hơn class CSS).
_POST_SELECTOR = "[data-e2e='search-result-post']"
_POST_ATTR = "data-e2e='search-result-post'"
# Threads login-wall: URL sau redirect chứa /login hoặc text nút "Log in".
_LOGIN_URL_RE = re.compile(r"threads\.net/login|accounts\.instagram\.com|facebook\.com/login", re.I)
_LOGIN_TEXT_RE = re.compile(r"\b(log\s?in|sign\s?up)\b", re.I)

# ── Cache in-memory TTL riêng (plan §3.3-bis: 10 phút, tách khỏi TTL Jina) ──
_DEFAULT_CACHE_TTL_S = 600
_cache: dict[str, tuple[float, list[TrendItem]]] = {}


def _get_cache_ttl_s() -> int:
    import os

    try:
        return max(60, int(os.getenv("CA_CAMOUFOX_CACHE_TTL_S", str(_DEFAULT_CACHE_TTL_S))))
    except ValueError:
        return _DEFAULT_CACHE_TTL_S


def _cache_key(keyword: str, nguon_goc: str) -> str:
    """Key gồm keyword + region (nguon_goc) — plan §3.3."""
    return f"threads:{(keyword or '').strip().lower()}|{nguon_goc}"


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


def _is_login_wall(html: str, url: str = "") -> bool:
    """Phát hiện login-wall: URL redirect về /login hoặc trang chỉ còn nút Log in.

    Plan §3.4: một số vùng/IP ép login → coi là unavailable, rớt tầng ngay.
    """
    if url and _LOGIN_URL_RE.search(url):
        return True
    # Trang search thật luôn có data-e2e post; nếu chỉ có nút login → wall.
    if _POST_ATTR not in html and _LOGIN_TEXT_RE.search(html):
        return True
    return False


def fetch_threads_page(page: Any, keyword: str) -> str:
    """Chờ SPA Threads search render xong danh sách post, trả HTML trang.

    KHÔNG goto ở đây — `scrape_page(url, extractor)` đã goto tới search URL
    trước khi gọi hàm này (tránh goto 2 lần). Chỉ lo phần chờ render.
    """
    # Chờ SPA render xong danh sách post (timeout do scrape_page quản).
    page.wait_for_selector(_POST_SELECTOR, timeout=30_000)
    content: str = page.content()
    return content


def extract_threads_items(
    html: str,
    keyword: str,
    count: int,
    nguon_goc: str,
    now_str: str,
) -> list[TrendItem]:
    """Hàm THUẦN: parse HTML Threads search → list[TrendItem].

    Không phụ thuộc Playwright — test bằng fixture HTML tĩnh. Khi Threads đổi
    DOM, chỉ cần cập nhật fixture + hàm này, không đụng browser lifecycle.
    """
    items_out: list[TrendItem] = []
    # Split theo khối post — mỗi khối chứa 1 post + stats.
    blocks = html.split(_POST_ATTR)
    for idx, block in enumerate(blocks[1:]):  # blocks[0] là phần trước post đầu
        if len(items_out) >= count:
            break
        try:
            item = _map_block(block, idx, keyword, nguon_goc, now_str)
            if item is not None:
                items_out.append(item)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "camoufox_threads_map_skipped idx=%d reason=%s",
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
    """Map 1 khối HTML post → TrendItem. Trả None nếu khối rỗng/lỗi parse."""
    from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword

    # Post URL: href dạng /@username/post/{id}
    post_url = ""
    m = re.search(r'href="(/@[\w\.\-]+/post/[\w]+)"', block_html)
    if m:
        post_url = f"https://www.threads.net{m.group(1)}"
    username_m = re.search(r"@([\w\.]+)", block_html)
    username = username_m.group(1) if username_m else "threads_creator"

    # Text hiển thị: strip thẻ HTML, lấy đoạn text dài nhất (> 30 ký tự).
    text_no_tags = re.sub(r"<[^>]+>", " ", block_html)
    text_no_tags = re.sub(r"\s+", " ", text_no_tags).strip()
    # Post text thường nằm trước stats — lấy 220 ký tự đầu làm nội dung thô.
    text_raw = text_no_tags[:220].strip()
    if len(text_raw) < 30:
        return None

    # Stats: pattern "số" lặp lại sau text — parse dạng 12.3K/1.2M (parser CHUNG).
    stat_nums = re.findall(r"(\d[\d.,]*\s*[KMB]?)\b", text_no_tags)
    parsed = [_parse_count(s) for s in stat_nums[:4]]
    likes = parsed[0] if parsed else 0
    replies = parsed[1] if len(parsed) > 1 else 0

    short_kw = keyword.strip() or extract_core_tiktok_keyword(text_raw) or username
    clean_tag = re.sub(r"[^a-zA-Z0-9_]", "", short_kw.lower())

    from urllib.parse import quote

    encoded_kw = quote(short_kw)
    th_search = f"https://www.threads.net/search?q={encoded_kw}"
    th_tag = f"https://www.threads.net/search?q=%23{clean_tag}" if clean_tag else th_search

    # Tái dùng helper CHUNG từ threads_direct_source (plan §3.4 — không copy code).
    vong_doi, growth, viral_score, forecast = _assess_trend_lifecycle(likes, replies, text_raw)
    category = _detect_category("", text_raw)
    reach_str = f"{likes:,} tim | {replies:,} phản hồi"

    first_line = text_raw.split("\n")[0].strip()
    title_display = first_line[:65] + ("..." if len(first_line) > 65 else "")

    return TrendItem(
        id=f"camoufox_threads_{idx}_{clean_tag or idx}",
        tieu_de=f"🧵 [THREADS VIRAL] {title_display}",
        cum_tu_khoa_viral=short_kw or "Tâm sự Threads",
        nguon_goc=nguon_goc,
        loai_xu_huong="breaking_vn_24h",
        danh_muc=category,
        vong_doi=vong_doi,
        diem_nhan_dac_biet=f"Tài khoản: @{username}. Tương tác thật: {reach_str}. Trạng thái: {forecast}",
        nguon_goc_chi_tiet=f"Cào qua Camoufox browser thật lúc {now_str}.",
        ngu_canh_su_dung=(
            f"Ý tưởng đổi mới đồ uống, nâng cao trải nghiệm không gian hoặc "
            f"sáng tạo bài đăng theo xu hướng #{short_kw}."
        ),
        tam_ly_gioi_tre="Tâm lý tiêu dùng, trải nghiệm không gian và gu thưởng thức đồ uống mới của Gen Z.",
        toc_do_tang_truong_24h=growth,
        diem_tiem_nang_viral=viral_score,
        du_bao_thoi_gian=forecast,
        link_goc=post_url or th_search,
        tiktok_url=th_search,
        tiktok_tag_url=th_tag,
        thoi_gian_cao=now_str,
        luot_tiep_can=reach_str,
        trich_doan_noi_dung_that=text_raw,
        binh_luan_that_tiktok=[],
        nen_tang_lan_toa=["Meta Threads"],
        tu_khoa_hashtag=[f"#{clean_tag}", "#threads", "#fnbvietnam", "#genz"],
        is_live_scraped=True,
    )


def scrape_threads_camoufox(
    keyword: str = "",
    count: int = 12,
    nguon_goc: str = "threads_vn",
) -> list[TrendItem]:
    """Cào Threads search qua Camoufox. Raise CamoufoxUnavailable nếu chưa cài/login-wall.

    Được gọi trong chuỗi `_scrape_threads_smart` giữa Jina direct và Apify.
    Cache TTL riêng CA_CAMOUFOX_CACHE_TTL_S (mặc định 10 phút, plan §3.3-bis).
    """
    from urllib.parse import quote

    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    start = time.monotonic()
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    key = _cache_key(keyword, nguon_goc)
    cached = _cache_get(key)
    if cached is not None:
        logger.info(
            "threads_source_camoufox_cache_hit",
            extra={
                "source": "camoufox",
                "keyword": keyword[:50],
                "items_count": len(cached),
                "duration_ms": int((time.monotonic() - start) * 1000),
            },
        )
        return cached[:count]

    kw = keyword.strip() or "fnb quan cafe gen z"
    url = f"https://www.threads.net/search?q={quote(kw)}&serp_type=default"

    def _extractor(page: Any) -> str:
        # Login-wall check: URL hiện tại sau redirect + HTML content.
        current_url = ""
        try:
            current_url = page.url or ""
        except Exception:  # noqa: BLE001
            current_url = ""
        html = fetch_threads_page(page, keyword)
        if _is_login_wall(html, current_url):
            # Plan §3.4: login-wall → unavailable cho lần gọi này, rớt tầng NGAY.
            raise CamoufoxUnavailable(
                "Threads yêu cầu đăng nhập (login-wall) — rớt tầng, không cố vượt (plan §2.3)"
            )
        return html

    html = scrape_page(url, _extractor)
    items = extract_threads_items(html, keyword, count, nguon_goc, now_str)
    if items:
        _cache_put(key, items)

    logger.info(
        "threads_source_camoufox",
        extra={
            "source": "camoufox",
            "nguon_goc": nguon_goc,
            "keyword": keyword[:50],
            "items_count": len(items),
            "duration_ms": int((time.monotonic() - start) * 1000),
        },
    )
    return items
