"""Nguồn dữ liệu xu hướng F&B từ Google Trends qua SerpApi.

Bắt các từ khóa đồ uống/món ăn đang bùng nổ tìm kiếm tại Việt Nam (geo=VN),
phân loại vòng đời xu hướng và trích xuất thành TrendItem cho AG-TREND.
Tuân thủ ADR-002, ADR-003, ADR-008.
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

logger = logging.getLogger(__name__)


def extract_interest_timeline(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Trích xuất chuỗi thời gian (time-series) mức độ quan tâm từ payload Google Trends."""
    timeline: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return timeline

    iot = payload.get("interest_over_time") or {}
    points = iot.get("timeline_data") or []
    for pt in points:
        if not isinstance(pt, dict):
            continue
        date_label = str(pt.get("date") or "")
        ts = str(pt.get("timestamp") or "")
        values = pt.get("values") or []
        val_int = 0
        if values and isinstance(values, list) and isinstance(values[0], dict):
            val_int = int(values[0].get("extracted_value") or values[0].get("value") or 0)

        timeline.append({
            "date": date_label,
            "timestamp": ts,
            "value": val_int,
        })
    return timeline


def parse_gtrends_to_trend_items(
    payload: dict[str, Any],
    query_keyword: str,
    include_timeline: bool = False,
) -> list[TrendItem]:
    """Parse payload Google Trends từ SerpApi thành danh sách TrendItem."""
    items: list[TrendItem] = []
    if not isinstance(payload, dict):
        return items

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    related = payload.get("related_queries") or {}
    rising_queries = related.get("rising") or []
    timeline = extract_interest_timeline(payload)

    # 1. Trích xuất các cụm từ khóa tìm kiếm đang tăng vọt (Rising / Breakout)
    for rq in rising_queries[:8]:
        if not isinstance(rq, dict):
            continue

        query_name = str(rq.get("query") or "").strip()
        if not query_name:
            continue

        raw_val = str(rq.get("value") or "")
        extracted_val = float(rq.get("extracted_value") or 0.0)

        is_breakout = "breakout" in raw_val.lower() or extracted_val >= 5000.0
        growth_rate = 5000.0 if is_breakout else (extracted_val if extracted_val > 0 else 300.0)

        if is_breakout:
            vong_doi = "moi_nhu"
            viral_score = 96
            du_bao = "🔥 Đang bùng nổ đột biến (Breakout >5000%) trên Google Tìm Kiếm VN trong 7 ngày qua"
        else:
            vong_doi = "dang_dinh" if growth_rate >= 500 else "moi_nhu"
            viral_score = 88 if growth_rate >= 500 else 82
            du_bao = f"⚡ Tìm kiếm tăng trưởng +{growth_rate:.0f}% so với tuần trước"

        trend_id = f"gtrend_{abs(hash(query_name)) % 10000000:07d}"

        items.append(
            TrendItem(
                id=trend_id,
                tieu_de=f"[Google Trends VN] Xu hướng: {query_name.title()}",
                cum_tu_khoa_viral=query_name,
                nguon_goc="google_vn",
                loai_xu_huong="breaking_vn_24h",
                danh_muc="am_thuc_fnb",
                vong_doi=vong_doi,
                diem_nhan_dac_biet=f"Từ khóa liên quan gốc '{query_keyword}', tăng trưởng tìm kiếm: {raw_val}",
                nguon_goc_chi_tiet=f"Dữ liệu Google Trends Việt Nam (SerpApi) cập nhật {now_iso}",
                ngu_canh_su_dung=(
                    f"Người tiêu dùng đang tăng vọt nhu cầu tìm kiếm '{query_name}'. "
                    "Quán có thể cân nhắc thử nghiệm đưa món vào menu đặc biệt (Seasonal/Special) "
                    "hoặc làm video ngắn/bài đăng Fanpage bắt kịp nhu cầu này."
                ),
                tam_ly_gioi_tre="Tò mò muốn trải nghiệm hương vị mới hoặc các biến thể sáng tạo của thức uống quen thuộc.",
                toc_do_tang_truong_24h=growth_rate,
                diem_tiem_nang_viral=viral_score,
                du_bao_thoi_gian=du_bao,
                thoi_gian_cao=now_iso,
                luot_tiep_can=f"+{growth_rate:.0f}% searches",
                trich_doan_noi_dung_that=f"Google Search Index: {query_name} ({raw_val})",
                nen_tang_lan_toa=["Google Search", "Google Trends"],
            )
        )

    # 2. Nếu bật include_timeline và có dữ liệu timeline cho từ khóa chính
    if include_timeline and timeline and len(timeline) >= 2:
        latest_pt = timeline[-1]["value"]
        prev_pt = timeline[-2]["value"]
        ts_growth = round(((latest_pt - prev_pt) / max(1, prev_pt)) * 100.0, 1)

        vong_doi_ts = "dang_dinh" if latest_pt >= 75 else ("moi_nhu" if ts_growth > 20 else "thoai_trao")
        main_trend_id = f"gtrend_ts_{abs(hash(query_keyword)) % 10000000:07d}"

        if not any(it.cum_tu_khoa_viral.lower() == query_keyword.lower() for it in items):
            items.insert(
                0,
                TrendItem(
                    id=main_trend_id,
                    tieu_de=f"[Google Trends Time-Series] Chỉ số quan tâm: {query_keyword.title()}",
                    cum_tu_khoa_viral=query_keyword,
                    nguon_goc="google_vn",
                    loai_xu_huong="breaking_vn_24h",
                    danh_muc="am_thuc_fnb",
                    vong_doi=vong_doi_ts,
                    diem_nhan_dac_biet=f"Chỉ số tìm kiếm đạt {latest_pt}/100 ({'+' if ts_growth >= 0 else ''}{ts_growth}% so với kỳ trước)",
                    nguon_goc_chi_tiet=f"Google Trends Time-Series ({len(timeline)} điểm dữ liệu)",
                    ngu_canh_su_dung=f"Theo dõi nhu cầu tiêu dùng cốt lõi đối với '{query_keyword}'.",
                    tam_ly_gioi_tre="Thói quen tiêu dùng chủ lực.",
                    toc_do_tang_truong_24h=float(ts_growth),
                    diem_tiem_nang_viral=latest_pt,
                    du_bao_thoi_gian=f"Chỉ số hiện tại: {latest_pt}/100",
                    thoi_gian_cao=now_iso,
                    luot_tiep_can=f"Score {latest_pt}/100",
                    trich_doan_noi_dung_that=f"{query_keyword}: {latest_pt}/100",
                    nen_tang_lan_toa=["Google Search", "Google Trends"],
                ),
            )

    # 3. Nếu không có rising, trích xuất top queries
    if not items:
        top_queries = related.get("top") or []
        for tq in top_queries[:5]:
            if not isinstance(tq, dict):
                continue
            query_name = str(tq.get("query") or "").strip()
            if not query_name:
                continue

            trend_id = f"gtrend_top_{abs(hash(query_name)) % 10000000:07d}"
            items.append(
                TrendItem(
                    id=trend_id,
                    tieu_de=f"[Google Trends Top] {query_name.title()}",
                    cum_tu_khoa_viral=query_name,
                    nguon_goc="google_vn",
                    loai_xu_huong="breaking_vn_24h",
                    danh_muc="am_thuc_fnb",
                    vong_doi="dang_dinh",
                    diem_nhan_dac_biet=f"Từ khóa ổn định trong nhóm '{query_keyword}'",
                    nguon_goc_chi_tiet=f"Dữ liệu Google Trends Việt Nam (Top Search) {now_iso}",
                    ngu_canh_su_dung=f"Nhu cầu nền tảng của khách hàng đối với '{query_name}'.",
                    tam_ly_gioi_tre="Thức uống quen thuộc hàng ngày.",
                    toc_do_tang_truong_24h=120.0,
                    diem_tiem_nang_viral=80,
                    du_bao_thoi_gian="Duy trì ổn định hàng tuần",
                    thoi_gian_cao=now_iso,
                    luot_tiep_can="High volume",
                    trich_doan_noi_dung_that=query_name,
                    nen_tang_lan_toa=["Google Search"],
                )
            )

    return items


def fetch_fnb_trends_serpapi(
    keyword: str = "cà phê",
    geo: str = "VN",
    date: str = "now 7-d",
    ttl_hours: float = 12.0,
    include_timeline: bool = False,
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> list[TrendItem]:
    """Lấy dữ liệu xu hướng tìm kiếm F&B từ Google Trends qua SerpApi.

    **Bắt buộc `data_type=RELATED_QUERIES`**: SerpApi mặc định trả TIMESERIES
    (chỉ có `interest_over_time`), payload khi đó **không có `related_queries`**
    nên `parse_gtrends_to_trend_items()` trả rỗng — đo live 2026-09-24:
    mặc định rising=0/top=0, `RELATED_QUERIES` rising=20/top=25.

    `include_timeline=True` cần thêm chuỗi thời gian → tốn **thêm 1 request**
    (2 request/lượt gọi). Mặc định chỉ 1 request để tiết kiệm quota 250/tháng.
    """
    base_params: dict[str, str] = {
        "q": keyword,
        "geo": geo,
        "date": date,
    }

    try:
        payload = search_serpapi(
            "google_trends",
            {**base_params, "data_type": "RELATED_QUERIES"},
            ttl_hours=ttl_hours,
            cache_dir=cache_dir,
            quota_path=quota_path,
            circuit_breaker=circuit_breaker,
        )

        # Chuỗi thời gian nằm ở payload TIMESERIES riêng — gọi thêm 1 request
        # và chỉ khi caller yêu cầu rõ (không làm mặc định để tiết kiệm quota).
        if include_timeline and isinstance(payload, dict):
            timeline_payload = search_serpapi(
                "google_trends",
                {**base_params, "data_type": "TIMESERIES"},
                ttl_hours=ttl_hours,
                cache_dir=cache_dir,
                quota_path=quota_path,
                circuit_breaker=circuit_breaker,
            )
            if isinstance(timeline_payload, dict) and timeline_payload.get(
                "interest_over_time"
            ):
                payload = {**payload, "interest_over_time": timeline_payload["interest_over_time"]}

        return parse_gtrends_to_trend_items(
            payload, query_keyword=keyword, include_timeline=include_timeline
        )
    except (SerpApiDisabledError, SerpApiQuotaExceededError, SerpApiCircuitOpenError) as exc:
        logger.warning("SerpApi Google Trends không khả dụng (%s), bỏ qua", exc)
        return []
    except SerpApiError as exc:
        logger.error("Lỗi khi truy vấn SerpApi Google Trends: %s", exc)
        return []
