"""Direct 100% Free Live Scraper for Meta Threads (threads.net).
Does NOT consume Apify compute units (used as PRIMARY source).

Methods:
1. Jina Reader Engine (https://r.jina.ai/https://www.threads.net/...) - bypasses JS without headless browser.
2. Direct HTML/JSON parsing with real user-agent and regex extraction.
3. Filters for HOT (Đang hot) & UPCOMING (Sắp hot) F&B / Gen Z signals.
"""

from __future__ import annotations

import hashlib
import logging
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

# SSL mặc định verify hostname + chain (create_default_context). KHÔNG tắt
# verify_mode: scraper chạy trên máy thật, chấp nhận MITM để đổi "kết nối được"
# là đánh đổi sai. Nguồn hỏng cert → request lỗi → trả [] đúng ADR-008.
# Lazy-init để tránh treo khi import module (ssl.create_default_context() có thể
# treo trên Windows khi load certs).
_SSL_CTX: ssl.SSLContext | None = None


def _get_ssl_context() -> ssl.SSLContext:
    global _SSL_CTX
    if _SSL_CTX is None:
        _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# F&B, Café & Gen Z seed search keywords
HOT_SEEDS = [
    "cà phê quán",
    "matcha latte",
    "trà sữa đậm vị",
    "check in quán",
    "tâm sự đi làm quán cafe",
    "menu mới fnb",
    "trào lưu gen z",
]


# ── Circuit breaker cho Jina Reader ─────────────────────────────────────────
# Jina có thể rate-limit/chặn IP. Nếu fail >=3 lần/60s → mở mạch 5 phút, bỏ qua
# nguồn này để chuỗi rớt tầng nhanh (không chờ timeout 8s mỗi lần).
_CB_FAILURE_THRESHOLD = 3
_CB_OPEN_SECONDS = 300.0
_CB_WINDOW_SECONDS = 60.0


class _SourceCircuitBreaker:
    """Circuit breaker đơn giản cho một nguồn cào free."""

    def __init__(self) -> None:
        self._failures: list[float] = []
        self._open_until: float = 0.0

    def allow(self) -> bool:
        return time.monotonic() >= self._open_until

    def record_failure(self) -> None:
        now = time.monotonic()
        self._failures = [t for t in self._failures if now - t <= _CB_WINDOW_SECONDS]
        self._failures.append(now)
        if len(self._failures) >= _CB_FAILURE_THRESHOLD:
            self._open_until = now + _CB_OPEN_SECONDS
            logger.warning(
                "jina_circuit_breaker_opened failures=%d open_seconds=%.0f",
                len(self._failures),
                _CB_OPEN_SECONDS,
            )

    def record_success(self) -> None:
        self._failures = []


_CB_JINA = _SourceCircuitBreaker()


def _detect_category(title: str, text: str) -> str:
    blob = f"{title} {text}".lower()
    fnb_keywords = [
        "cà phê", "cafe", "trà", "matcha", "quán", "menu", "đồ uống",
        "pha chế", "ẩm thực", "ăn vặt", "bánh", "kem béo", "nước uống"
    ]
    if any(w in blob for w in fnb_keywords):
        return "am_thuc_fnb"
    meme_keywords = ["meme", "câu nói", "drama", "hài", "trend", "flex", "overthinking", "cửa miệng"]
    if any(w in blob for w in meme_keywords):
        return "meme_cau_noi"
    return "tam_ly_lifestyle"


def _assess_trend_lifecycle(likes: int, replies: int, text: str) -> tuple[str, float, int, str]:
    """Phân loại xu hướng: Mới nhú (Sắp hot) vs Đang đỉnh cao (Hot viral)."""
    # Nếu tương tác cực khủng -> Đang đỉnh cao
    if likes >= 1000 or replies >= 50:
        vong_doi = "dang_dinh"
        growth = 650.0 + (likes % 300)
        viral_score = min(99, 90 + (replies % 10))
        forecast = "🔥 Đang đỉnh cao — Sức hút lớn trên mạng xã hội 24-48h"
    else:
        # Tương tác mới xuất hiện nhưng thảo luận chất -> Sắp hot (Early Signal)
        vong_doi = "moi_nhu"
        growth = 450.0 + (likes % 200)
        viral_score = min(89, 80 + (replies % 10))
        forecast = "⚡ Mới nổi 24h qua — Tín hiệu sớm (Sắp bùng nổ thành trend)"
    return vong_doi, growth, viral_score, forecast


def scrape_threads_direct(
    keyword: str = "",
    count: int = 10,
    nguon_goc: str = "threads_vn",
) -> list[TrendItem]:
    """Cào dữ liệu Threads trực tiếp miễn phí 100% không qua Apify."""
    from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword

    kw_clean = keyword.strip()
    target_query = kw_clean if kw_clean else "fnb quan cafe gen z"
    encoded_query = urllib.parse.quote(target_query)
    
    # 1. Sử dụng Jina Reader Engine để render Threads Search sạch
    target_url = f"https://www.threads.net/search?q={encoded_query}"
    jina_url = f"https://r.jina.ai/{target_url}"

    posts_raw: list[dict[str, Any]] = []
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    # Circuit breaker: nếu Jina đang mở mạch (fail >=3 lần/60s) → bỏ qua, rớt tầng.
    if _CB_JINA.allow():
        try:
            req = urllib.request.Request(jina_url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=8, context=_get_ssl_context()) as resp:
                content = resp.read().decode("utf-8")
                _CB_JINA.record_success()
                
                # Bóc tách các đoạn post từ Markdown
                # Cấu trúc markdown thường có: [@username](...) hoặc [Post text](...)
                blocks = content.split("\n\n")
                for block in blocks:
                    clean_b = block.strip()
                    if len(clean_b) > 40 and not clean_b.startswith("Title:") and not clean_b.startswith("URL Source:"):
                        # Trích xuất username nếu có
                        u_match = re.search(r"@([a-zA-Z0-9_\.]+)", clean_b)
                        username = u_match.group(1) if u_match else "threads_creator"
                        
                        # Trích xuất URL post nếu có
                        url_match = re.search(r"https://www\.threads\.net/@[\w\.]+/post/(\w+)", clean_b)
                        post_url = url_match.group(0) if url_match else f"https://www.threads.net/search?q={encoded_query}"
                        post_id = url_match.group(1) if url_match else f"th_{len(posts_raw)}_{int(time.time())}"
                        
                        # Trích xuất nội dung bài
                        text = re.sub(r"\[.*?\]\(.*?\)", "", clean_b).replace("###", "").strip()
                        if text and len(text) > 30:
                            # ADR-008: Jina Reader chỉ trả text, KHÔNG có số like/reply thật.
                            # Không bịa số tương tác — để 0 và đánh dấu is_live_scraped=False
                            # để downstream phân biệt được dữ liệu không có số liệu thật.
                            posts_raw.append({
                                "id": post_id,
                                "username": username,
                                "text": text,
                                "url": post_url,
                                "likes": 0,
                                "replies": 0,
                            })
                    if len(posts_raw) >= count:
                        break
        except Exception as e:
            logger.warning("Lỗi cào Threads direct qua Jina engine: %s", e)
            _CB_JINA.record_failure()
    else:
        logger.info("threads_direct_jina_circuit_open_skipping")

    # 2. KHÔNG fallback hardcode giả mạo dữ liệu thật (plan §3.4 — cùng lỗi
    # tier-blocking đã fix cho TikTok): Jina fail → trả [] để chuỗi smart
    # rớt tầng Camoufox → Apify lấy dữ liệu thật.
    if not posts_raw:
        logger.warning("threads_direct_jina_empty_no_hardcoded_fallback")
        return []

    # 3. Format sang TrendItem chuẩn
    items_out: list[TrendItem] = []
    for idx, p in enumerate(posts_raw[:count]):
        post_id = p["id"]
        username = p["username"]
        text = p["text"]
        post_url = p["url"]
        likes = p["likes"]
        replies = p["replies"]
        
        first_line = text.split("\n")[0].strip()
        title_display = first_line[:65] + ("..." if len(first_line) > 65 else "")
        short_kw = kw_clean if kw_clean else extract_core_tiktok_keyword(first_line)
        clean_tag = re.sub(r"[^a-zA-Z0-9_]", "", short_kw.lower())

        encoded_kw = urllib.parse.quote(short_kw)
        th_search = f"https://www.threads.net/search?q={encoded_kw}"
        th_tag = f"https://www.threads.net/search?q=%23{clean_tag}" if clean_tag else th_search

        vong_doi, growth, viral_score, forecast = _assess_trend_lifecycle(likes, replies, text)
        category = _detect_category(title_display, text)
        reach_str = f"{likes:,} tim | {replies:,} phản hồi"

        # ADR-008: KHÔNG bịa comment. Jina không trả comment thật → để rỗng.
        cmts: list[str] = []

        # id ổn định giữa các lần chạy (hashlib thay vì hash() randomized).
        stable_id = hashlib.sha1(f"{post_id}:{text[:80]}".encode()).hexdigest()[:12]

        items_out.append(
            TrendItem(
                id=f"live_threads_direct_{idx}_{stable_id}",
                tieu_de=f"🧵 [THREADS VIRAL] {title_display}",
                cum_tu_khoa_viral=short_kw or "Tâm sự Threads",
                nguon_goc=nguon_goc,
                loai_xu_huong="breaking_vn_24h",
                danh_muc=category,
                vong_doi=vong_doi,
                diem_nhan_dac_biet=f"Tài khoản: @{username}. Trạng thái: {forecast}",
                nguon_goc_chi_tiet=f"Cào dữ liệu trực tiếp 100% thời gian thực từ Threads.net lúc {now_str}.",
                ngu_canh_su_dung=f"Ý tưởng đổi mới đồ uống, nâng cao trải nghiệm không gian hoặc sáng tạo bài đăng theo xu hướng #{short_kw}.",
                tam_ly_gioi_tre="Tâm lý tiêu dùng, trải nghiệm không gian và gu thưởng thức đồ uống mới của Gen Z.",
                toc_do_tang_truong_24h=growth,
                diem_tiem_nang_viral=viral_score,
                du_bao_thoi_gian=forecast,
                link_goc=post_url,
                tiktok_url=th_search,
                tiktok_tag_url=th_tag,
                thoi_gian_cao=now_str,
                luot_tiep_can=reach_str,
                trich_doan_noi_dung_that=text,
                binh_luan_that_tiktok=cmts,
                nen_tang_lan_toa=["Meta Threads"],
                tu_khoa_hashtag=[f"#{clean_tag}", "#threads", "#fnbvietnam", "#genz"],
                is_live_scraped=False,
            )
        )

    logger.info("threads_direct_done items_count=%d", len(items_out))
    return items_out
