"""Nguồn thu thập dữ liệu ShopeeFood qua SerpApi Google Maps.

Cung cấp dữ liệu chuẩn 100% (tên quán, địa chỉ, rating, review count)
thay thế cho cơ chế cào Camoufox bị chặn captcha/403.
Tuân thủ ADR-002, ADR-003, ADR-008 và Nghị định 13/2023/NĐ-CP.

Chiến lược:
- Sử dụng SerpApi Google Maps engine để tìm kiếm quán F&B
- Tìm kiếm với từ khóa "shopeefood" hoặc "delivery" kết hợp với category
- Parse kết quả từ Google Maps local_results
- Lọc và chuẩn hóa dữ liệu thành StoreCandidate
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

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


def _is_shopeefood_related(item: dict[str, Any]) -> bool:
    """Kiểm tra xem quán có liên quan đến ShopeeFood không."""
    # Kiểm tra tên quán
    name = str(item.get("title") or "").lower()
    if "shopeefood" in name or "shopee food" in name:
        return True
    
    # Kiểm tra mô tả
    description = str(item.get("description") or "").lower()
    if "shopeefood" in description or "shopee food" in description:
        return True
    
    # Kiểm tra loại hình
    place_type = str(item.get("type") or "").lower()
    if "delivery" in place_type or "food delivery" in place_type:
        return True
    
    # Kiểm tra extensions (thường chứa thông tin về dịch vụ)
    extensions = item.get("extensions") or []
    if isinstance(extensions, list):
        for ext in extensions:
            if isinstance(ext, str) and ("shopeefood" in ext.lower() or "delivery" in ext.lower()):
                return True
    
    return False


def parse_shopeefood_serpapi_results(
    payload: dict[str, Any],
    origin_lat: float,
    origin_lng: float,
    radius_km: float = 5.0,
    data_source: Literal["serpapi", "camoufox", "cache", "delivery_platform"] = "serpapi",
) -> list[StoreCandidate]:
    """Parse payload JSON từ SerpApi Google Maps thành danh sách StoreCandidate ShopeeFood."""
    candidates: list[StoreCandidate] = []
    if not isinstance(payload, dict):
        return candidates

    now_iso = datetime.now(timezone.utc).isoformat()
    raw_items = payload.get("local_results") or []
    
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        
        # Chỉ lấy các quán liên quan đến ShopeeFood
        if not _is_shopeefood_related(item):
            continue
        
        store_id = str(item.get("place_id") or item.get("data_id") or "")
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

        # Trích xuất thông tin ShopeeFood từ extensions
        shopeefood_info = []
        extensions = item.get("extensions") or []
        if isinstance(extensions, list):
            for ext in extensions:
                if isinstance(ext, str):
                    if "delivery" in ext.lower():
                        shopeefood_info.append("delivery")
                    if "shopeefood" in ext.lower():
                        shopeefood_info.append("shopeefood")

        # Tạo description mở rộng với thông tin ShopeeFood
        description = str(item.get("description") or "")
        if shopeefood_info:
            description += f" [ShopeeFood: {', '.join(shopeefood_info)}]"

        candidates.append(
            StoreCandidate(
                id=store_id,
                place_id=store_id,
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
                # Sử dụng sold_count_text để lưu thông tin ShopeeFood
                sold_count_text=f"shopeefood:{','.join(shopeefood_info)}" if shopeefood_info else "",
            )
        )

    return candidates


def fetch_shopeefood_competitors_serpapi(
    latitude: float,
    longitude: float,
    keyword: str,
    radius_km: float = 5.0,
    ttl_hours: float = 24.0,
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> list[StoreCandidate]:
    """Tìm kiếm đối thủ ShopeeFood quanh quán bằng SerpApi Google Maps.
    
    Chiến lược tìm kiếm:
    1. Tìm kiếm với từ khóa "shopeefood" + keyword
    2. Tìm kiếm với từ khóa "delivery" + keyword
    3. Kết hợp kết quả và loại trùng
    """
    queries = [
        f"shopeefood {keyword}",
        f"delivery {keyword}",
        f"{keyword} giao hàng",
    ]
    
    all_candidates: list[StoreCandidate] = []
    seen_ids: set[str] = set()
    
    for query in queries:
        # Format toạ độ theo chuẩn Google Maps: @lat,lng,zoom
        zoom = 15 if radius_km <= 3.0 else (14 if radius_km <= 7.0 else 13)
        ll_param = f"@{latitude},{longitude},{zoom}z"

        params = {
            "q": query.strip(),
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
            candidates = parse_shopeefood_serpapi_results(
                payload,
                origin_lat=latitude,
                origin_lng=longitude,
                radius_km=radius_km,
                data_source=data_source,
            )
            
            # Loại trùng dựa trên place_id
            for candidate in candidates:
                if candidate.id not in seen_ids:
                    seen_ids.add(candidate.id)
                    all_candidates.append(candidate)
                    
        except (SerpApiDisabledError, SerpApiQuotaExceededError, SerpApiCircuitOpenError) as exc:
            logger.warning("SerpApi ShopeeFood không khả dụng (%s), chuyển fallback", exc)
            raise
        except SerpApiError as exc:
            logger.error("Lỗi SerpApi ShopeeFood: %s", exc)
            continue
        except Exception as exc:
            logger.error("Lỗi không xác định khi gọi SerpApi ShopeeFood: %s", exc)
            continue
    
    return all_candidates


def fetch_shopeefood_menu_serpapi(
    place_id: str,
    ttl_hours: float = 168.0,  # 7 ngày cho menu photos
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> list[str]:
    """Lấy ảnh menu từ ShopeeFood qua SerpApi Google Maps Photos.
    
    Returns:
        Danh sách URL ảnh menu
    """
    params = {
        "data_id": place_id,
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
        
        # Trích xuất ảnh menu từ response
        photos = payload.get("photos") or []
        menu_urls: list[str] = []
        
        for photo in photos:
            if isinstance(photo, dict):
                # Ưu tiên ảnh có title chứa "menu" hoặc "thực đơn"
                title = str(photo.get("title") or "").lower()
                if "menu" in title or "thực đơn" in title or "thuc don" in title:
                    url = photo.get("image") or photo.get("thumbnail")
                    if url and isinstance(url, str) and url.startswith("http"):
                        menu_urls.append(url)
        
        # Nếu không tìm thấy ảnh menu cụ thể, trả về ảnh đầu tiên
        if not menu_urls and photos:
            first_photo = photos[0] if isinstance(photos[0], dict) else {}
            url = first_photo.get("image") or first_photo.get("thumbnail")
            if url and isinstance(url, str) and url.startswith("http"):
                menu_urls.append(url)
        
        return menu_urls
        
    except (SerpApiDisabledError, SerpApiQuotaExceededError, SerpApiCircuitOpenError) as exc:
        logger.warning("SerpApi ShopeeFood Photos không khả dụng (%s)", exc)
        raise
    except SerpApiError as exc:
        logger.error("Lỗi SerpApi ShopeeFood Photos: %s", exc)
        return []