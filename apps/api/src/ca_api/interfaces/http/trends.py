"""
HTTP Router for Pure AI Trend Intelligence & Live Scraper.
"""

from __future__ import annotations

from typing import Annotated, Any

from ca_agents.ag_trend import (
    TrendItem,
    fetch_trend_radar,
    get_trend_by_id,
)
from ca_agents.clients.apify_client import get_apify_usage
from fastapi import APIRouter, Header, HTTPException, Query

from ca_api.persist import session as auth_session

router = APIRouter(prefix="/api/v1/trends", tags=["trends"])


def _require_auth(authorization: str | None) -> dict[str, Any]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="chua_dang_nhap")
    return s


def _serialize_trend(t: TrendItem) -> dict[str, Any]:
    return {
        "id": t.id,
        "tieu_de": t.tieu_de,
        "cum_tu_khoa_viral": t.cum_tu_khoa_viral,
        "nguon_goc": t.nguon_goc,
        "loai_xu_huong": t.loai_xu_huong,
        "danh_muc": t.danh_muc,
        "vong_doi": t.vong_doi,
        "diem_nhan_dac_biet": t.diem_nhan_dac_biet,
        "nguon_goc_chi_tiet": t.nguon_goc_chi_tiet,
        "ngu_canh_su_dung": t.ngu_canh_su_dung,
        "tam_ly_gioi_tre": t.tam_ly_gioi_tre,
        "toc_do_tang_truong_24h": t.toc_do_tang_truong_24h,
        "diem_tiem_nang_viral": t.diem_tiem_nang_viral,
        "du_bao_thoi_gian": t.du_bao_thoi_gian,
        "link_goc": t.link_goc,
        "tiktok_url": t.tiktok_url,
        "tiktok_tag_url": t.tiktok_tag_url,
        "thoi_gian_cao": t.thoi_gian_cao,
        "luot_tiep_can": t.luot_tiep_can,
        "trich_doan_noi_dung_that": t.trich_doan_noi_dung_that,
        "binh_luan_that_tiktok": getattr(t, "binh_luan_that_tiktok", []),
        "nen_tang_lan_toa": t.nen_tang_lan_toa,
        "tu_khoa_hashtag": t.tu_khoa_hashtag,
        "is_live_scraped": t.is_live_scraped,
    }


@router.get("/apify-usage")
def get_apify_usage_status(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Fetch current Apify quota, monthly usage & active actors."""
    _require_auth(authorization)
    usage = get_apify_usage()
    return {"ok": True, "usage": usage}


@router.get("/radar")
def get_trends_radar(
    region: str = Query(default="all"),
    category: str = Query(default="all"),
    keyword: str = Query(default=""),
    mode: str = Query(default="auto"),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Fetch real-time scraped trends with news excerpts, TikTok videos & comments."""
    _require_auth(authorization)
    trends = fetch_trend_radar(
        platform_filter=region, category_filter=category, keyword=keyword, scrape_mode=mode
    )
    return {
        "ok": True,
        "total": len(trends),
        "region_filter": region,
        "category_filter": category,
        "keyword_filter": keyword,
        "scrape_mode": mode,
        "trends": [_serialize_trend(t) for t in trends],
    }


@router.get("/{trend_id}")
def get_trend_detail(
    trend_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Fetch deep intelligence analysis for a single trend."""
    _require_auth(authorization)
    trend = get_trend_by_id(trend_id)
    if not trend:
        raise HTTPException(status_code=404, detail="trend_not_found")

    return {
        "ok": True,
        "trend": _serialize_trend(trend),
    }
