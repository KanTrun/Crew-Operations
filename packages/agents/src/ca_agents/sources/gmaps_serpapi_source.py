"""Nguồn thu thập đối thủ Google Maps & Menu Photos qua SerpApi.

Cung cấp dữ liệu chuẩn 100% (rating thật, review thật, tọa độ GPS thật)
thay thế cho cơ chế cào nặng nề và nợ kỹ thuật hardcode của Camoufox.
Tuân thủ ADR-002, ADR-003, ADR-008 và Nghị định 13/2023/NĐ-CP.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ca_contracts.catchment_survey import StoreCandidate

from ca_agents.clients.serpapi_client import (
    CircuitBreaker,
    SerpApiCircuitOpenError,
    SerpApiDisabledError,
    SerpApiError,
    SerpApiQuotaExceededError,
    search_serpapi,
)

logger = logging.getLogger(__name__)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách đường chim bay giữa 2 tọa độ (km)."""
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    a_clamped = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a_clamped), math.sqrt(1.0 - a_clamped))
    return round(r * c, 2)


def _parse_rating(val: Any) -> float:
    """Parse điểm đánh giá an toàn, kẹp trong khoảng [0.0, 5.0]."""
    if val is None:
        return 0.0
    try:
        r = float(val)
        return max(0.0, min(5.0, round(r, 1)))
    except (ValueError, TypeError):
        return 0.0


def _parse_review_count(val: Any) -> int:
    """Parse số lượng đánh giá an toàn, hỗ trợ '1,250', '1.2k', số nguyên."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return max(0, int(val))
    val_str = str(val).strip().lower()
    if not val_str or val_str.startswith("-"):
        return 0
    # Xử lý format "1.2k" / "1,2k"
    if "k" in val_str:
        num_part = val_str.replace("k", "").replace(",", ".").strip()
        try:
            return max(0, int(float(num_part) * 1000))
        except (ValueError, TypeError):
            pass
    # Xử lý format có dấu phẩy hoặc text thừa (vd: "1,250 đánh giá")
    cleaned = re.sub(r"[^\d]", "", val_str)
    try:
        return max(0, int(cleaned)) if cleaned else 0
    except (ValueError, TypeError):
        return 0


def parse_gmaps_results_to_candidates(
    payload: dict[str, Any],
    origin_lat: float,
    origin_lng: float,
    radius_km: float = 3.0,
    data_source: str = "serpapi",
) -> list[StoreCandidate]:
    """Parse payload JSON từ SerpApi Google Maps thành danh sách StoreCandidate hợp lệ."""
    candidates: list[StoreCandidate] = []
    if not isinstance(payload, dict):
        return candidates

    now_iso = datetime.now(timezone.utc).isoformat()
    raw_items = payload.get("local_results") or []
    for item in raw_items:
        if not isinstance(item, dict):
            continue

        store_id = str(item.get("place_id") or item.get("data_id") or "")
        data_id = str(item.get("data_id") or "")
        name = str(item.get("title") or "").strip()
        if not name or not store_id:
            continue

        rating = _parse_rating(item.get("rating"))
        review_count = _parse_review_count(item.get("reviews"))
        address = str(item.get("address") or "")

        # Tọa độ GPS & Khoảng cách thật
        gps = item.get("gps_coordinates") or {}
        dest_lat = float(gps.get("latitude") or 0.0)
        dest_lng = float(gps.get("longitude") or 0.0)

        if dest_lat != 0.0 and dest_lng != 0.0:
            dist_km = haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
        else:
            dist_km = 0.5  # Giá trị ước tính mặc định nếu thiếu GPS

        # Bộ lọc bán kính: bỏ qua các quán vượt quá bán kính cho phép
        if radius_km > 0 and dist_km > radius_km:
            continue

        # Trích xuất ảnh thumbnail / photos
        menu_images: list[str] = []
        thumb = item.get("thumbnail")
        if thumb and isinstance(thumb, str) and thumb.startswith("http"):
            menu_images.append(thumb)

        candidates.append(
            StoreCandidate(
                id=store_id,
                place_id=store_id,
                data_id=data_id,
                name=name,
                address=address,
                lat=dest_lat,
                lng=dest_lng,
                distance_km=dist_km,
                rating=rating,
                review_count=review_count,
                url=str(item.get("place_id_search") or ""),
                menu_image_urls=menu_images,
                dishes=[],
                data_source=data_source,
                fetched_at=now_iso,
            )
        )

    return candidates


def fetch_gmaps_competitors_serpapi(
    latitude: float,
    longitude: float,
    keyword: str,
    radius_km: float = 3.0,
    ttl_hours: float = 24.0,
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> list[StoreCandidate]:
    """Tìm kiếm đối thủ quanh quán bằng SerpApi Google Maps."""
    query = keyword.strip() or "quán cà phê"
    # Format toạ độ theo chuẩn Google Maps: @lat,lng,zoom
    # Zoom 15z tương đương bán kính ~2-3km, 14z ~5km
    zoom = 15 if radius_km <= 3.0 else (14 if radius_km <= 7.0 else 13)
    ll_param = f"@{latitude},{longitude},{zoom}z"

    params = {
        "q": query,
        "ll": ll_param,
        "hl": "vi",
        "gl": "vn",
        "type": "search",
    }

    try:
        payload = search_serpapi(
            "google_maps",
            params,
            ttl_hours=ttl_hours,
            cache_dir=cache_dir,
            quota_path=quota_path,
            circuit_breaker=circuit_breaker,
        )
        data_source = "cache" if payload.get("data_source") == "cache" else "serpapi"
        return parse_gmaps_results_to_candidates(
            payload,
            origin_lat=latitude,
            origin_lng=longitude,
            radius_km=radius_km,
            data_source=data_source,
        )
    except (SerpApiDisabledError, SerpApiQuotaExceededError, SerpApiCircuitOpenError) as exc:
        logger.warning("SerpApi Google Maps không khả dụng (%s), chuyển fallback", exc)
        raise
    except SerpApiError as exc:
        logger.error("Lỗi SerpApi Google Maps: %s", exc)
        return []


def fetch_gmaps_menu_photos_serpapi(
    place_id: str,
    max_images: int = 5,
    ttl_hours: float = 168.0,  # 7 ngày
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    data_id: str = "",
) -> list[str]:
    """Lấy danh sách ảnh album thực đơn (Menu) của quán đối thủ qua SerpApi.

    SerpApi engine `google_maps_photos` yêu cầu tham số `data_id` (mã định danh
    quán trong Google Maps), KHÔNG phải `place_id`. Nếu không có `data_id`,
    SerpApi trả 400 "Missing query `data_id` parameter".
    """
    # Ưu tiên data_id (bắt buộc cho google_maps_photos); fallback place_id.
    lookup_id = data_id or place_id
    if not lookup_id:
        return []

    params = {
        "data_id": lookup_id,
        "hl": "vi",
        "gl": "vn",
    }

    try:
        payload = search_serpapi(
            "google_maps_photos",
            params,
            ttl_hours=ttl_hours,
            cache_dir=cache_dir,
            quota_path=quota_path,
            circuit_breaker=circuit_breaker,
        )
    except Exception as exc:
        logger.warning("Không lấy được ảnh menu qua SerpApi: %s", exc)
        return []

    photos: list[str] = []
    photos_data = payload.get("photos") or []
    for p in photos_data:
        if not isinstance(p, dict):
            continue
        image_url = p.get("image") or p.get("thumbnail")
        if image_url and isinstance(image_url, str) and image_url.startswith("http"):
            photos.append(image_url)
            if len(photos) >= max_images:
                break

    return photos


def fetch_gmaps_reviews_serpapi(
    place_id: str,
    max_reviews: int = 10,
    ttl_hours: float = 24.0,
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> list[dict[str, Any]]:
    """Lấy reviews của quán và ẩn danh hóa thông tin cá nhân (Nghị định 13/2023/NĐ-CP)."""
    if not place_id:
        return []

    params = {
        "place_id": place_id,
        "hl": "vi",
        "gl": "vn",
    }

    try:
        payload = search_serpapi(
            "google_maps_reviews",
            params,
            ttl_hours=ttl_hours,
            cache_dir=cache_dir,
            quota_path=quota_path,
            circuit_breaker=circuit_breaker,
        )
    except Exception as exc:
        logger.warning("Không lấy được reviews qua SerpApi: %s", exc)
        return []

    raw_reviews = payload.get("reviews") or []
    anonymized_reviews: list[dict[str, Any]] = []

    for r in raw_reviews:
        if not isinstance(r, dict):
            continue
        # Bóc tách nội dung nghiệp vụ, LOẠI BỎ tên người dùng, avatar, user_id (Bảo vệ DLCN)
        snippet = str(r.get("snippet") or "")
        rating = _parse_rating(r.get("rating"))
        date_str = str(r.get("date") or "")

        anonymized_reviews.append({
            "rating": rating,
            "snippet": snippet,
            "date": date_str,
            "anonymized": True,
        })
        if len(anonymized_reviews) >= max_reviews:
            break

    return anonymized_reviews
