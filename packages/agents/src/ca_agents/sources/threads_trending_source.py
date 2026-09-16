"""Cào danh sách 'Trending Now' (Xu hướng hiện tại) trên Threads bằng Camoufox.

Đặc thù nghiệp vụ:
    Bảng 'Trending Now' tại threads.net/search chỉ hiển thị đầy đủ cho tài khoản
    đã đăng nhập (Authenticated Session Profile với user_data_dir). Với khách vãng lai,
    Meta sẽ khóa hoặc chỉ hiển thị form đăng nhập (login-wall).

Thiết kế tách bạch (Architecture Blueprint):
    - fetch_threads_trending_page(page)      — chờ render danh sách Trending Now.
    - extract_threads_trending_items(html)   — hàm THUẦN, test bằng fixture HTML/JSON tĩnh.
    - scrape_threads_trending(...)           — orchestrate qua camoufox_client.scrape_page
                                              với user_data_dir + cache TTL riêng.

Circuit breaker (plan §V Lớp 4):
    Khi phát hiện dấu hiệu checkpoint (URL /login//challenge/, form xác minh
    danh tính, HTTP 429) → đặt cờ CRITICAL_PAUSE tắt toàn bộ chu kỳ cào tiếp
    theo cho tới khi quản trị viên reset tay. KHÔNG tự retry để không tăng
    điểm rủi ro tài khoản.

Tái dùng từ source có sẵn (ADR-003, plan §3.4):
    - `_detect_category` từ `threads_direct_source`.
    - `_parse_count` từ `tiktok_camoufox_source`.

Public API:
    scrape_threads_trending(user_data_dir=None, count=12, nguon_goc="threads_vn") -> list[TrendItem]
    extract_threads_trending_snapshot(html, ...) -> ThreadsTrendingSnapshot
    circuit_breaker_status() / circuit_breaker_reset() — quản lý ngắt mạch.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from ca_contracts.threads_trending import ThreadsTrendingItem

from ca_agents.clients.camoufox_client import scrape_page
from ca_agents.sources.threads_direct_source import _detect_category
from ca_agents.sources.threads_trending_lifecycle import (
    ChuKyTruoc,
    gan_nhan_snapshot,
    tinh_trang_thai_chu_ky_sau,
)
from ca_agents.sources.tiktok_camoufox_source import _parse_count

# Map lifecycle (plan §4.2) → vong_doi TrendItem (từ vựng ag_trend).
_LIFECYCLE_TO_VONG_DOI = {
    "NEW": "moi_nhu",
    "RISING": "moi_nhu",
    "PEAKING": "dang_dinh",
    "FADING": "bao_hoa",
}

# Lịch sử chu kỳ cho lifecycle (module-level, process-wide).
_lifecycle_history: dict[str, ChuKyTruoc] = {}
_lifecycle_last_seen: dict[str, float] = {}

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

# URL bảng tìm kiếm & Trending Now
_SEARCH_URL = "https://www.threads.net/search"

# Selector nhận diện danh sách trending trên giao diện
_TRENDING_CONTAINER_SELECTOR = "[role='main']"
_LOGIN_LINK_SELECTOR = "a[href*='/login']"
_POST_COUNT_RE = re.compile(r"(\d[\d.,]*\s*[KMB]?)\s*(?:posts|bài viết)\b", re.I)

# ── Circuit breaker (plan §V Lớp 4) ──────────────────────────────────────────
# Dấu hiệu checkpoint: URL chứa /login/ hoặc /challenge/, form xác minh danh tính
# (tải ảnh giấy tờ), hoặc HTTP 429 Too Many Requests. Gặp BẤT KỲ dấu hiệu nào →
# CRITICAL_PAUSE: dừng mọi chu kỳ cào tiếp theo tới khi quản trị viên reset tay.
_CHECKPOINT_URL_RE = re.compile(r"/(login|challenge)/", re.I)
_CHECKPOINT_TEXT_RE = re.compile(
    r"verify your identity|xác minh danh tính|upload a photo of yourself|"
    r"tải ảnh giấy tờ|too many requests",
    re.I,
)

# Trạng thái circuit breaker (process-wide, thread-safe bằng GIL cho read-modify đơn giản)
_cb_state: dict[str, Any] = {
    "paused": False,
    "reason": "",
    "paused_at": None,
}


def circuit_breaker_status() -> dict[str, Any]:
    """Trạng thái circuit breaker hiện tại (cho monitoring/runbook)."""
    return dict(_cb_state)


def circuit_breaker_reset() -> None:
    """Reset circuit breaker — CHỈ quản trị viên gọi sau khi xử lý xong sự cố."""
    _cb_state.update({"paused": False, "reason": "", "paused_at": None})


def _circuit_breaker_trip(reason: str) -> None:
    """Kích hoạt CRITICAL_PAUSE. Idempotent — giữ lý do ĐẦU TIÊN không ghi đè."""
    if not _cb_state["paused"]:
        _cb_state.update(
            {
                "paused": True,
                "reason": reason,
                "paused_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    logger.critical("threads_trending_circuit_breaker_tripped reason=%s", reason)


def _detect_checkpoint(url: str, html: str) -> str | None:
    """Trả mô tả dấu hiệu checkpoint nếu phát hiện, None nếu an toàn.

    Hàm THUẦN — test bằng fixture, không cần browser.
    """
    # Defensive: ensure url is string (test mocks may pass MagicMock)
    url_str = str(url) if url else ""
    if _CHECKPOINT_URL_RE.search(url_str):
        return f"URL chuyển hướng chứa login/challenge: {url_str[:120]}"
    if _CHECKPOINT_TEXT_RE.search(html or ""):
        m = _CHECKPOINT_TEXT_RE.search(html or "")
        return f"Trang hiển thị form xác minh/rate-limit: {m.group(0) if m else 'unknown'}"
    return None


# Cache TTL riêng cho Trending Now (mặc định 15 phút, vì Trending cập nhật 15-30 phút/lần)
_DEFAULT_CACHE_TTL_S = 900
_cache: dict[str, tuple[float, list[TrendItem]]] = {}


def _get_cache_ttl_s() -> int:
    import os

    try:
        return max(60, int(os.getenv("CA_THREADS_TRENDING_CACHE_TTL_S", str(_DEFAULT_CACHE_TTL_S))))
    except ValueError:
        return _DEFAULT_CACHE_TTL_S


def _cache_key(nguon_goc: str) -> str:
    return f"threads_trending:{nguon_goc}"


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
    """Reset cache (dùng trong unit test)."""
    _cache.clear()


def fetch_threads_trending_page(page: Any) -> str:
    """Chờ trang search render danh sách Trending Now, trả về toàn bộ HTML/DOM.

    Kiểm tra trạng thái xác thực: Nếu trang chỉ hiển thị login-wall mà không
    có nội dung tìm kiếm hoặc trending, raise CamoufoxUnavailable để thông báo
    cần can thiệp cấu hình profile.

    Circuit breaker (plan §V Lớp 4): dấu hiệu checkpoint (URL /challenge/,
    form xác minh, 429) → trip CRITICAL_PAUSE NGAY trước khi trả nội dung.
    """
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    try:
        page.wait_for_selector(_TRENDING_CONTAINER_SELECTOR, timeout=20_000)
    except Exception as e:  # noqa: BLE001
        raise CamoufoxUnavailable(
            f"Threads search không tải được vùng nội dung chính sau 20s: {type(e).__name__}"
        ) from e

    # Kiểm tra login-wall
    try:
        has_login = page.query_selector(_LOGIN_LINK_SELECTOR) is not None
    except Exception:  # noqa: BLE001
        has_login = False

    content: str = page.content()

    # Circuit breaker: checkpoint check trên URL hiện tại + HTML
    try:
        current_url: str = page.url or ""
    except Exception:  # noqa: BLE001
        current_url = ""
    checkpoint = _detect_checkpoint(current_url, content)
    if checkpoint:
        _circuit_breaker_trip(checkpoint)
        raise CamoufoxUnavailable(
            f"CHECKPOINT PHÁT HIỆN — circuit breaker đã kích hoạt CRITICAL_PAUSE: {checkpoint}"
        )

    # Nếu có link login và không có từ khóa 'posts' hay 'bài viết' → phiên chưa đăng nhập
    if has_login and not _POST_COUNT_RE.search(content):
        raise CamoufoxUnavailable(
            "Yêu cầu đăng nhập: Danh mục Trending Now của Threads chỉ hiển thị "
            "với tài khoản đã đăng nhập. Vui lòng thiết lập CA_THREADS_USER_DATA_DIR."
        )

    return content


def _parse_trending_from_embedded_json(html: str) -> list[dict[str, Any]]:
    """Trích xuất từ các khối JSON nhúng (Relay / BigPipe GraphQL responses)."""
    results: list[dict[str, Any]] = []
    # Tìm các script json
    scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for s in scripts:
        if "trending" not in s.lower() and "topic" not in s.lower():
            continue
        try:
            data = json.loads(s)
            _extract_json_nodes(data, results)
        except Exception:  # noqa: BLE001
            pass
    return results


def _extract_json_nodes(obj: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(obj, dict):
        # Kiểm tra node có hình hài của trending topic
        title = obj.get("title") or obj.get("topic_name") or obj.get("name")
        post_count = obj.get("post_count") or obj.get("posts_count")
        if title and post_count is not None and isinstance(title, str):
            out.append({
                "title": title.strip(),
                "summary": str(obj.get("description") or obj.get("subtitle") or "").strip(),
                "post_count": int(post_count) if str(post_count).isdigit() else _parse_count(str(post_count)),
                "thumbnail_url": obj.get("thumbnail_url") or obj.get("image_url") or "",
            })
        for v in obj.values():
            _extract_json_nodes(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _extract_json_nodes(item, out)


def _parse_trending_from_dom_blocks(html: str) -> list[dict[str, Any]]:
    """Trích xuất danh sách xu hướng từ cấu trúc HTML DOM ngữ nghĩa.

    Cấu trúc hiển thị chuẩn của Threads:
      - Tiêu đề (dòng in đậm/h1/h2/div lớn)
      - Mô tả ngữ cảnh kèm " · [X] posts" hoặc " · [X] bài viết"
      - Ảnh thumbnail kèm theo
    """
    results: list[dict[str, Any]] = []

    # Quét trực tiếp các đoạn văn bản có chứa pattern "[X] posts"
    # Định dạng: Tiêu đề + Ngữ cảnh · [X] posts
    lines = [line.strip() for line in re.sub(r"<[^>]+>", "\n", html).split("\n") if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        match = _POST_COUNT_RE.search(line)
        if match:
            # line chứa "9K posts" hoặc "· 9K posts"
            # Thường ngữ cảnh nằm trong chính line này hoặc dòng ngay trước đó
            volume_raw = match.group(0)
            volume_num = _parse_count(match.group(1))

            # Nếu dòng này có dấu phân cách '·' hoặc bullet
            parts = re.split(r"[·•]", line)
            if len(parts) >= 2:
                summary = parts[0].strip()
                # Tiêu đề nằm ở dòng trước đó
                title = lines[i - 1] if i > 0 else summary
            else:
                # Dòng hiện tại chỉ có "9K posts", dòng trước là summary, dòng trước nữa là title
                summary = lines[i - 1] if i > 0 else ""
                title = lines[i - 2] if i > 1 else summary

            # Làm sạch tiêu đề
            clean_title = re.sub(r"^[0-9]+[.\s]+", "", title).strip()
            if clean_title and len(clean_title) >= 3 and not _POST_COUNT_RE.search(clean_title):
                # Tìm ảnh thumbnail gần vị trí này nếu có
                results.append({
                    "title": clean_title,
                    "summary": summary,
                    "post_count": volume_num,
                    "volume_raw": volume_raw,
                    "thumbnail_url": "",
                })
        i += 1

    # Khử trùng lặp theo tiêu đề
    seen_titles: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in results:
        t_key = r["title"].lower()
        if t_key not in seen_titles:
            seen_titles.add(t_key)
            deduped.append(r)

    return deduped


def _make_topic_id(title: str) -> str:
    """Mã băm ổn định từ tiêu đề đã chuẩn hoá (plan §4.1: `topic_id`)."""
    normalized = re.sub(r"\s+", " ", title.strip().lower())
    return f"th_trend_{hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:7]}"


def extract_threads_trending_snapshot(
    html: str,
    count: int = 12,
    now: datetime | None = None,
) -> list[ThreadsTrendingItem]:
    """Hàm THUẦN: HTML → list[ThreadsTrendingItem] theo contract plan §4.1.

    Đây là hợp đồng dữ liệu chuẩn hoá (ADR-003) — tách khỏi `TrendItem`
    hiển thị. `lifecycle` để placeholder "NEW"; việc gán nhãn thật do
    `lifecycle_tracker.gan_nhan_snapshot` làm (cần dữ liệu chu kỳ trước).
    """
    if not html:
        return []
    if now is None:
        now = datetime.now(timezone.utc)

    raw_items = _parse_trending_from_embedded_json(html)
    if not raw_items:
        raw_items = _parse_trending_from_dom_blocks(html)

    out: list[ThreadsTrendingItem] = []
    for rank, raw in enumerate(raw_items[:count], start=1):
        title = (raw.get("title") or "").strip()
        if not title:
            continue
        post_count = int(raw.get("post_count") or 0)
        volume_raw = raw.get("volume_raw") or f"{post_count:,} posts"
        summary = (raw.get("summary") or "").strip()
        out.append(
            ThreadsTrendingItem(
                topic_id=_make_topic_id(title),
                rank=rank,
                title=title,
                summary=summary,
                volume_raw=volume_raw,
                volume_count=post_count,
                thumbnail_url=(raw.get("thumbnail_url") or "").strip(),
                search_url=f"https://www.threads.net/search?q={quote(title)}",
                lifecycle="NEW",  # placeholder — gán nhãn thật ở lifecycle_tracker
                scraped_at=now,
            )
        )
    return out


def extract_threads_trending_items(
    html: str,
    count: int = 12,
    nguon_goc: str = "threads_vn",
    now_str: str | None = None,
) -> list[TrendItem]:
    """Hàm THUẦN: Phân tích cú pháp HTML/JSON → list[TrendItem].

    Test được độc lập bằng fixture HTML tĩnh mà không cần khởi động trình duyệt.
    """
    from ca_agents.ag_trend import TrendItem

    if not html:
        return []

    if now_str is None:
        now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    # 1. Thử trích xuất từ JSON nhúng trước (Kênh chính)
    raw_items = _parse_trending_from_embedded_json(html)

    # 2. Nếu JSON không có, fallback sang phân tích DOM text blocks (Kênh phụ)
    if not raw_items:
        raw_items = _parse_trending_from_dom_blocks(html)

    items_out: list[TrendItem] = []
    for rank, raw in enumerate(raw_items[:count], start=1):
        title = raw.get("title", "").strip()
        if not title:
            continue

        summary = raw.get("summary", "").strip()
        post_count = raw.get("post_count", 0)
        volume_raw = raw.get("volume_raw") or f"{post_count:,} posts"

        # Vòng đời: >= 10K thảo luận coi như 'dang_dinh', dưới đó coi như 'moi_nhu'
        vong_doi = "dang_dinh" if post_count >= 10_000 else "moi_nhu"
        category = _detect_category("", f"{title} {summary}")

        search_url = f"https://www.threads.net/search?q={quote(title)}"
        clean_tag = re.sub(r"[^a-zA-Z0-9_]", "", title.lower())

        item = TrendItem(
            id=_make_topic_id(title),
            tieu_de=f"🔥 [THREADS TREND #{rank}] {title}",
            cum_tu_khoa_viral=title,
            nguon_goc=nguon_goc,
            loai_xu_huong="breaking_vn_24h",
            danh_muc=category,
            vong_doi=vong_doi,
            diem_nhan_dac_biet=(
                f"Thứ hạng: #{rank}. Thảo luận: {volume_raw}. "
                f"{summary if summary else 'Xu hướng đang thịnh hành trên Threads VN.'}"
            ),
            nguon_goc_chi_tiet=f"Cào bảng Trending Now Threads qua Camoufox lúc {now_str}.",
            ngu_canh_su_dung=f"Nắm bắt tin tức nóng #{title} để sáng tạo nội dung bắt trend hoặc thảo luận cùng khách hàng.",
            tam_ly_gioi_tre="Tâm điểm chú ý và đề tài thảo luận nổi bật của giới trẻ trên Threads trong ngày.",
            toc_do_tang_truong_24h=float(min(300, 50 + rank * 15)),
            diem_tiem_nang_viral=max(75, 95 - rank * 2),
            du_bao_thoi_gian="24h - 48h tới",
            link_goc=search_url,
            tiktok_url=search_url,
            tiktok_tag_url=search_url,
            thoi_gian_cao=now_str,
            luot_tiep_can=volume_raw,
            trich_doan_noi_dung_that=f"{title}\n{summary}",
            binh_luan_that_tiktok=[],
            nen_tang_lan_toa=["Meta Threads"],
            tu_khoa_hashtag=[f"#{clean_tag[:15]}", "#threads", "#trending", "#vietnam"],
            is_live_scraped=True,
        )
        items_out.append(item)

    return items_out


def scrape_threads_trending(
    user_data_dir: str | None = None,
    count: int = 12,
    nguon_goc: str = "threads_vn",
) -> list[TrendItem]:
    """Cào bảng Trending Now Threads qua Camoufox với Profile đã đăng nhập.

    Raise CamoufoxUnavailable nếu chưa cài đặt Camoufox, phiên chưa xác thực,
    HOẶC circuit breaker đang CRITICAL_PAUSE (checkpoint đã được phát hiện —
    quản trị viên phải reset tay sau khi xử lý, không tự retry).
    """
    global _lifecycle_history, _lifecycle_last_seen
    from ca_agents.clients.camoufox_client import CamoufoxUnavailable

    # Circuit breaker: nếu đã trip → không launch browser, không tăng rủi ro tài khoản.
    if _cb_state["paused"]:
        raise CamoufoxUnavailable(
            f"Circuit breaker CRITICAL_PAUSE đang bật (từ {_cb_state['paused_at']}): "
            f"{_cb_state['reason']} — cần quản trị viên xử lý rồi "
            f"gọi circuit_breaker_reset()."
        )

    start = time.monotonic()
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    key = _cache_key(nguon_goc)
    cached = _cache_get(key)
    if cached is not None:
        logger.info(
            "threads_trending_cache_hit",
            extra={
                "source": "camoufox_trending",
                "items_count": len(cached),
                "duration_ms": int((time.monotonic() - start) * 1000),
            },
        )
        return cached[:count]

    def _extractor(page: Any) -> str:
        return fetch_threads_trending_page(page)

    html = scrape_page(_SEARCH_URL, _extractor, user_data_dir=user_data_dir)

    # Bước 1: contract snapshot (ADR-003) — lifecycle placeholder NEW.
    snapshot_items = extract_threads_trending_snapshot(html, count=count)
    # Bước 2: gán nhãn vòng đời thật bằng lịch sử chu kỳ trước (plan §4.2).
    snapshot_items = gan_nhan_snapshot(
        snapshot_items, _lifecycle_history, _lifecycle_last_seen
    )
    # Bước 3: cập nhật lịch sử cho chu kỳ sau.
    _lifecycle_history = tinh_trang_thai_chu_ky_sau(snapshot_items, _lifecycle_history)
    _lifecycle_last_seen = {
        it.topic_id: time.time() for it in snapshot_items
    }

    # Bước 4: map contract → TrendItem hiển thị (vong_doi theo lifecycle).
    items = extract_threads_trending_items(html, count=count, nguon_goc=nguon_goc, now_str=now_str)
    # Gán nhãn vong_doi từ lifecycle đã tính (NEW/RISING→moi_nhu, PEAKING→dang_dinh, FADING→bao_hoa)
    lifecycle_by_topic = {it.topic_id: it.lifecycle for it in snapshot_items}
    # TrendItem là frozen dataclass → tạo list mới với vong_doi đã cập nhật
    items = [
        (
            item.__class__(
                **{**item.__dict__, "vong_doi": _LIFECYCLE_TO_VONG_DOI.get(
                    lifecycle_by_topic.get(item.id, "NEW"), item.vong_doi
                )}
            )
            if lifecycle_by_topic.get(item.id)
            else item
        )
        for item in items
    ]

    if items:
        _cache_put(key, items)

    logger.info(
        "threads_trending_scraped",
        extra={
            "source": "camoufox_trending",
            "nguon_goc": nguon_goc,
            "items_count": len(items),
            "duration_ms": int((time.monotonic() - start) * 1000),
        },
    )
    return items
