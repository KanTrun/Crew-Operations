"""Nguồn xu hướng Google Trends "Trending Now" cấp quốc gia qua SerpApi.

Khác với `gtrends_serpapi_source.fetch_fnb_trends_serpapi` (truy vấn theo
**từ khóa cụ thể** → chỉ trả biến thể liên quan), engine
`google_trends_trending_now` trả **bảng xếp hạng xu hướng tìm kiếm đang bùng nổ
tại một quốc gia** tại thời điểm gọi — không cần biết trước từ khóa.

Đã xác minh live 2026-09-24 (geo=VN): 21–25 mục, mỗi mục có:
    query, search_volume (số tuyệt đối), increase_percentage,
    categories[{id,name}], trend_breakdown[] (truy vấn con),
    start_timestamp (epoch giây), active.

Tài liệu: https://serpapi.com/google-trends-trending-now

Public API:
    fetch_trending_now_serpapi(geo="VN", hl="vi", count=12) -> list[TrendItem]

Tuân thủ ADR-002 (điều phối tất định), ADR-003 (contracts-first),
ADR-008 (chỉ trích xuất dữ liệu thật, không bịa số liệu tương tác).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ca_agents.ag_trend import TrendItem
from ca_agents.clients.serpapi_client import (
    CircuitBreaker,
    SerpApiCircuitOpenError,
    SerpApiDisabledError,
    SerpApiError,
    SerpApiQuotaExceededError,
    search_serpapi,
)
from ca_agents.text_util import match_any_keyword

logger = logging.getLogger(__name__)

# Danh mục F&B phát hiện theo TÊN category của Google Trends, không theo ID:
# bảng ID không được công bố ổn định và đoán sai ID sẽ gán nhãn sai nghiệp vụ
# (đo live 2026-09-24: "giá xăng dầu hôm nay" bị gán am_thuc_fnb khi dò theo ID).
_FNB_CATEGORY_NAMES = (
    "food",
    "drink",
    "dining",
    "restaurant",
    "cooking",
    "beverage",
    "bakery",
)
_FNB_KEYWORDS = (
    "cà phê",
    "cafe",
    "trà",
    "matcha",
    "quán",
    "menu",
    "đồ uống",
    "ẩm thực",
    "ăn",
    "bánh",
    "kem",
    "nước",
    "food",
    "coffee",
    "milk tea",
)
_MEME_KEYWORDS = ("meme", "drama", "hài", "trend", "show", "ca sĩ", "diễn viên", "genz", "gen z")


def _is_fnb_category(category_names: list[str]) -> bool:
    """True nếu bất kỳ tên category nào thuộc nhóm đồ ăn/uống."""
    return match_any_keyword(" ".join(category_names).lower(), _FNB_CATEGORY_NAMES)


def _match_keyword(blob: str, keywords: tuple[str, ...]) -> bool:
    """So khớp từ khoá theo **ranh giới từ**, không phải substring.

    Bắt buộc: `_FNB_KEYWORDS` có `"ăn"` — so khớp substring sẽ khớp cả trong
    `"xăng"` → `"giá xăng dầu hôm nay"` bị gán nhãn F&B (bug đo live 2026-09-24).
    Dùng helper chung `ca_agents.text_util.match_any_keyword`.
    """
    return match_any_keyword(blob, keywords)


def _detect_category(query: str, breakdown: list[str]) -> str:
    """Phân loại danh mục — thuần từ văn bản, không dùng số liệu ngoài."""
    blob = f"{query} {' '.join(breakdown)}".lower()
    if _match_keyword(blob, _FNB_KEYWORDS):
        return "am_thuc_fnb"
    if _match_keyword(blob, _MEME_KEYWORDS):
        return "trao_luu_pop_culture"
    return "tam_ly_lifestyle"


def _format_volume(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _vong_doi_from_increase(increase_pct: int) -> tuple[str, str]:
    """Map `increase_percentage` → (vong_doi, mô tả dự báo).

    Google Trends Trending Now dùng thang tăng trưởng phần trăm so với kỳ trước.
    """
    if increase_pct >= 1000:
        return "moi_nhu", "Đang bùng nổ đột biến (>1000% so với kỳ trước)"
    if increase_pct >= 400:
        return "moi_nhu", f"Tăng trưởng rất mạnh (+{increase_pct}%)"
    if increase_pct >= 100:
        return "dang_dinh", f"Tăng trưởng mạnh (+{increase_pct}%)"
    return "dang_dinh", f"Duy trì mức quan tâm cao (+{increase_pct}%)"


def parse_trending_now_payload(
    payload: dict[str, Any], geo: str = "VN", max_items: int = 25
) -> list[TrendItem]:
    """Hàm THUẦN: payload `google_trends_trending_now` → list[TrendItem].

    Tách khỏi phần gọi mạng để test được bằng fixture JSON tĩnh.
    """
    items: list[TrendItem] = []
    if not isinstance(payload, dict):
        return items

    searches = payload.get("trending_searches")
    if not isinstance(searches, list):
        return items

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    for idx, raw in enumerate(searches[:max_items]):
        if not isinstance(raw, dict):
            continue
        query = str(raw.get("query") or "").strip()
        if not query:
            continue

        volume = int(raw.get("search_volume") or 0)
        increase = int(raw.get("increase_percentage") or 0)
        breakdown_raw = raw.get("trend_breakdown")
        breakdown = [str(b) for b in breakdown_raw] if isinstance(breakdown_raw, list) else []
        categories = raw.get("categories")
        cat_names: list[str] = []
        if isinstance(categories, list):
            for c in categories:
                if isinstance(c, dict) and c.get("name"):
                    cat_names.append(str(c["name"]))

        danh_muc = "am_thuc_fnb" if _is_fnb_category(cat_names) else _detect_category(query, breakdown)

        vong_doi, forecast = _vong_doi_from_increase(increase)
        volume_str = _format_volume(volume) if volume else "không rõ"

        # `start_timestamp` là epoch giây lúc xu hướng bắt đầu bùng.
        started_at = raw.get("start_timestamp")
        started_str = ""
        if isinstance(started_at, (int, float)) and started_at > 0:
            try:
                started_str = datetime.fromtimestamp(started_at, tz=timezone.utc).strftime(
                    "%H:%M %d/%m"
                )
            except (OverflowError, OSError, ValueError):
                started_str = ""

        cat_str = f" [{', '.join(cat_names)}]" if cat_names else ""
        breakdown_str = f" Truy vấn con: {', '.join(breakdown[:6])}." if breakdown else ""

        items.append(
            TrendItem(
                id=f"gtrending_{geo.lower()}_{idx}_{abs(hash(query)) % 10_000_000:07d}",
                tieu_de=f"📈 [TRENDING {geo}] {query} ({volume_str} lượt tìm kiếm)",
                cum_tu_khoa_viral=query,
                nguon_goc="google_vn" if geo.upper() == "VN" else "tiktok_global",
                loai_xu_huong="breaking_vn_24h" if geo.upper() == "VN" else "predictive_global",
                danh_muc=danh_muc,
                vong_doi=vong_doi,
                diem_nhan_dac_biet=(
                    f"Bảng xếp hạng Google Trends Trending Now ({geo}){cat_str}. "
                    f"Lượng tìm kiếm: {volume:,} lượt. Tăng trưởng: +{increase}%."
                    + (f" Bắt đầu bùng từ {started_str}." if started_str else "")
                ),
                nguon_goc_chi_tiet=(
                    f"Google Trends Trending Now — bảng xếp hạng quốc gia qua SerpApi lúc {now_iso}."
                ),
                ngu_canh_su_dung=(
                    f"Xu hướng '{query}' đang được tìm kiếm nhiều tại {geo}. "
                    "Cân nhắc nội dung bắt trend, thử nghiệm món/menu đặc biệt, "
                    "hoặc điều chỉnh thông điệp truyền thông theo chủ đề này."
                ),
                tam_ly_gioi_tre=(
                    "Đám đông đang đồng loạt quan tâm — cửa sổ vàng để xuất hiện "
                    "trong lúc chủ đề còn nóng."
                ),
                toc_do_tang_truong_24h=float(increase),
                diem_tiem_nang_viral=min(98, 70 + increase // 50),
                du_bao_thoi_gian=forecast,
                link_goc=f"https://trends.google.com/trends/explore?q={query}&geo={geo}",
                tiktok_url=f"https://www.tiktok.com/search?q={query}",
                tiktok_tag_url="",
                thoi_gian_cao=now_iso,
                luot_tiep_can=f"{volume:,} lượt tìm kiếm".replace(",", "."),
                trich_doan_noi_dung_that=(
                    f"Google Trends Trending Now ({geo}): {query}.{breakdown_str}"
                ),
                binh_luan_that_tiktok=[],
                nen_tang_lan_toa=["Google Search", "Google Trends"],
                tu_khoa_hashtag=[f"#{query.replace(' ', '')}"[:30], "#trending", f"#{geo.lower()}"],
                is_live_scraped=True,
            )
        )

    return items


def fetch_trending_now_serpapi(
    geo: str = "VN",
    hl: str = "vi",
    count: int = 12,
    ttl_hours: float = 1.0,
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> list[TrendItem]:
    """Lấy bảng xếp hạng Google Trends Trending Now tại `geo` qua SerpApi.

    TTL 1 giờ (ngắn hơn Trends theo từ khóa 12h) vì đây là bảng xếp hạng
    **thời gian thực**, đổi vài chục phút/lần.

    Raise KHÔNG ném ra ngoài — lỗi/quota/circuit → trả [] để chuỗi rớt tầng.
    """
    params = {
        "geo": geo,
        "hl": hl,
    }
    try:
        payload = search_serpapi(
            "google_trends_trending_now",
            params,
            ttl_hours=ttl_hours,
            cache_dir=cache_dir,
            quota_path=quota_path,
            circuit_breaker=circuit_breaker,
        )
        items = parse_trending_now_payload(payload, geo=geo)
        logger.info(
            "serpapi_trending_now_ok geo=%s items_count=%d",
            geo,
            len(items),
        )
        return items[:count]
    except (SerpApiDisabledError, SerpApiQuotaExceededError, SerpApiCircuitOpenError) as exc:
        logger.warning("SerpApi Trending Now không khả dụng (%s), bỏ qua", exc)
        return []
    except SerpApiError as exc:
        logger.error("Lỗi khi truy vấn SerpApi Trending Now: %s", exc)
        return []


__all__ = [
    "fetch_trending_now_serpapi",
    "parse_trending_now_payload",
]
