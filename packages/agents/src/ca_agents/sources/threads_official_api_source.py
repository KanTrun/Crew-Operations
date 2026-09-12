"""Threads Official API (graph.threads.net) — keyword search public posts.

Meta đã mở endpoint GET /keyword_search cho phép search public posts bằng
keyword (docs: developers.facebook.com/docs/threads/keyword-search).

Đây là nguồn CHÍNH THỨC, hợp lệ, miễn phí — đặt tier ĐẦU TIÊN trong chuỗi
_scrape_threads_smart (trước Google Bridge) vì:
    - Data thật 100% từ Meta, không sợ bị chặn IP / login-wall
    - Rate limit hào phóng: 2,200 queries / 24h / user (queries rỗng không tính)
    - Không cần browser, không cần Apify CU

Yêu cầu cấu hình (env):
    THREADS_ACCESS_TOKEN  — OAuth user token có permission:
        threads_basic + threads_keyword_search
    (App chưa qua App Review → chỉ search posts của chính user đó;
     sau App Review → search toàn bộ public posts.)

Public API:
    is_configured() -> bool
    scrape_threads_official_api(keyword, count, nguon_goc) -> list[TrendItem]
    Raise ThreadsOfficialApiError nếu token sai / API lỗi → caller rớt tầng.
    Trả [] nếu search hợp lệ nhưng 0 kết quả (không phải lỗi).
"""

from __future__ import annotations

import json
import logging
import os
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ca_agents.ag_trend import TrendItem

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.threads.net/v1.0/keyword_search"
_SSL_CTX = ssl.create_default_context()

_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)

# Fields theo docs: id,text,media_type,permalink,timestamp,username,has_replies,
# is_quote_post,is_reply. owner bị loại trừ bởi API.
_FIELDS = "id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply"


class ThreadsOfficialApiError(RuntimeError):
    """Lỗi gọi Threads Official API (token sai, API lỗi, network)."""


def _get_token() -> str:
    token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    if not token:
        raise ThreadsOfficialApiError("THREADS_ACCESS_TOKEN chưa cấu hình trong env")
    return token


def is_configured() -> bool:
    """Có token Threads Official API trong env không."""
    return bool(os.getenv("THREADS_ACCESS_TOKEN", "").strip())


def _http_get_json(url: str, timeout: int = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            payload: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            return payload
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
            msg = body.get("error", {}).get("message", "") or str(body)[:200]
        except Exception:  # noqa: BLE001
            msg = str(e)[:200]
        raise ThreadsOfficialApiError(f"HTTP {e.code}: {msg}") from e
    except Exception as e:  # noqa: BLE001
        raise ThreadsOfficialApiError(f"{type(e).__name__}: {e}") from e


def _format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _extract_hashtags(text: str) -> list[str]:
    return [f"#{m.lower()}" for m in _HASHTAG_RE.findall(text)]


def _detect_category(title: str, text: str) -> str:
    blob = f"{title} {text}".lower()
    fnb = ["cà phê", "cafe", "cà", "trà", "matcha", "quán", "menu", "đồ uống", "pha chế", "ẩm thực", "ăn vặt", "bánh"]
    if any(w in blob for w in fnb):
        return "am_thuc_fnb"
    meme = ["meme", "câu nói", "drama", "hài", "trend", "flex", "overthinking"]
    if any(w in blob for w in meme):
        return "meme_cau_noi"
    return "tam_ly_lifestyle"


def _assess_lifecycle(idx: int, text: str) -> tuple[str, float, int, str]:
    """Đánh giá vòng đời + tốc độ tăng trưởng theo vị trí kết quả search TOP."""
    blob = text.lower()
    if idx == 0:
        vong_doi = "dinh_dinh"
        toc_do = 920.0
        diem_viral = 98
    elif idx <= 2:
        vong_doi = "dang_dinh"
        toc_do = max(400.0, 880.0 - idx * 120)
        diem_viral = max(88, 96 - idx)
    else:
        vong_doi = "dang_phinh"
        toc_do = max(250.0, 760.0 - idx * 90)
        diem_viral = max(75, 92 - idx * 2)
    if any(w in blob for w in ["trend", "viral", "hot", "bùng nổ", "đình đám"]):
        vong_doi = "dinh_dinh"
    du_bao = "Đang thu hút thảo luận mạnh trong 24-48h qua"
    return vong_doi, toc_do, diem_viral, du_bao


def _parse_timestamp(ts: str) -> str:
    """ISO 8601 → 'HH:MM:SS DD/MM/YYYY' (giờ địa phương)."""
    try:
        dt = datetime.fromisoformat(ts.replace("+0000", "+00:00"))
        return dt.astimezone().strftime("%H:%M:%S %d/%m/%Y")
    except (ValueError, TypeError):
        return datetime.now().strftime("%H:%M:%S %d/%m/%Y")


def _build_search_url(keyword: str, count: int, search_type: str) -> str:
    params = {
        "q": keyword,
        "fields": _FIELDS,
        "search_type": search_type,  # TOP | RECENT
        "limit": min(max(count, 1), 100),
        "access_token": _get_token(),
    }
    return f"{GRAPH_URL}?{urllib.parse.urlencode(params)}"


def _keyword_search(keyword: str, count: int, search_type: str = "TOP") -> list[dict[str, Any]]:
    """Gọi GET /keyword_search, trả list data[]. Raise nếu lỗi HTTP/API."""
    url = _build_search_url(keyword, count, search_type)
    payload = _http_get_json(url)
    data = payload.get("data")
    if not isinstance(data, list):
        raise ThreadsOfficialApiError(f"Response không hợp lệ: {str(payload)[:200]}")
    return data


def scrape_threads_official_api(
    keyword: str = "",
    count: int = 12,
    nguon_goc: str = "threads_vn",
    search_type: str = "TOP",
) -> list[TrendItem]:
    """Cào public posts Threads qua Official API keyword search.

    Trả [] nếu search hợp lệ nhưng 0 kết quả (queries rỗng không tốn quota).
    Raise ThreadsOfficialApiError nếu token sai / API lỗi → caller rớt tầng.
    """
    from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword

    _get_token()  # validate token sớm — raise nếu thiếu
    kw_clean = keyword.strip()

    # Không keyword → dùng bộ từ khóa mặc định F&B/Gen Z VN
    queries = [kw_clean] if kw_clean else ["cà phê", "gen z", "quán cafe"]
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    items_out: list[TrendItem] = []
    seen_ids: set[str] = set()

    for q in queries:
        try:
            data = _keyword_search(q, count, search_type)
        except ThreadsOfficialApiError as e:
            logger.warning("threads_official_api_query_failed q=%r: %s", q, str(e)[:200])
            raise
        if not data:
            logger.info("threads_official_api_empty q=%r (không tốn quota)", q)
            continue
        for idx, item in enumerate(data):
            post_id = str(item.get("id") or "")
            if not post_id or post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            text = str(item.get("text") or "").strip()
            username = str(item.get("username") or "threads_user")
            permalink = str(item.get("permalink") or f"https://www.threads.net/@{username}/post/{post_id}")
            ts_raw = str(item.get("timestamp") or "")
            thoi_gian_cao = _parse_timestamp(ts_raw)
            media_type = str(item.get("media_type") or "TEXT")

            first_line = text.split("\n")[0].strip() if text else ""
            title_display = first_line[:65] + ("..." if len(first_line) > 65 else "")
            short_kw = kw_clean if kw_clean else extract_core_tiktok_keyword(first_line or text)
            clean_tag = re.sub(r"[^a-zA-Z0-9_]", "", short_kw.lower())

            encoded_kw = urllib.parse.quote(short_kw)
            th_search = f"https://www.threads.net/search?q={encoded_kw}"
            th_tag = f"https://www.threads.net/search?q=%23{clean_tag}" if clean_tag else th_search

            tags = _extract_hashtags(text)
            if f"#{clean_tag}" not in tags and clean_tag:
                tags.insert(0, f"#{clean_tag}")
            if "#threads" not in tags:
                tags.append("#threads")

            vong_doi, toc_do, diem_viral, du_bao = _assess_lifecycle(idx, text)
            category = _detect_category(title_display, text)

            media_label = {"TEXT": "Bài text", "IMAGE": "Ảnh", "VIDEO": "Video"}.get(media_type, "Bài viết")
            has_replies = bool(item.get("has_replies"))

            items_out.append(
                TrendItem(
                    id=f"live_threads_api_{post_id}",
                    tieu_de=f"🧵 [THREADS API] {title_display or f'Bài viết của @{username}'}",
                    cum_tu_khoa_viral=short_kw or "Tâm sự Threads",
                    nguon_goc=nguon_goc,
                    loai_xu_huong="breaking_vn_24h",
                    danh_muc=category,
                    vong_doi=vong_doi,
                    diem_nhan_dac_biet=f"Tài khoản: @{username}. {media_label}. Có phản hồi: {'có' if has_replies else 'không'}.",
                    nguon_goc_chi_tiet=f"Cào qua Threads Official API (graph.threads.net) lúc {now_str}.",
                    ngu_canh_su_dung="Chủ đề tâm sự, bàn luận sôi nổi của giới trẻ Gen Z trên Threads.",
                    tam_ly_gioi_tre="Phong cách sống, ẩm thực và trải nghiệm của giới trẻ hiện nay.",
                    toc_do_tang_truong_24h=toc_do,
                    diem_tiem_nang_viral=diem_viral,
                    du_bao_thoi_gian=du_bao,
                    link_goc=permalink,
                    tiktok_url=th_search,
                    tiktok_tag_url=th_tag,
                    thoi_gian_cao=thoi_gian_cao,
                    luot_tiep_can=f"{media_label} từ Official API",
                    trich_doan_noi_dung_that=text[:250] + ("..." if len(text) > 250 else ""),
                    binh_luan_that_tiktok=[],
                    nen_tang_lan_toa=["Meta Threads"],
                    tu_khoa_hashtag=tags[:5],
                    is_live_scraped=True,
                )
            )
            if len(items_out) >= count:
                break
        if len(items_out) >= count:
            break

    logger.info("threads_official_api_done items=%d queries=%d", len(items_out), len(queries))
    return items_out
