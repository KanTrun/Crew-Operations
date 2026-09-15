"""Cào dữ liệu quán và menu đối thủ F&B bằng Camoufox (ShopeeFood / Delivery).

Tuân thủ thiết kế:
- fetch_delivery_page(page, ...): Điều hướng trình duyệt, bắt JSON API nội bộ.
- extract_delivery_stores_from_json(data): Hàm THUẦN, test bằng fixture offline.
- extract_delivery_stores_from_html(html): Parser HTML dự phòng.
- scrape_delivery_stores_camoufox(...): Orchestrate qua camoufox_client.scrape_page + cache TTL.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from ca_contracts.catchment_survey import DishItem, StoreCandidate

from ca_agents.clients.camoufox_client import CamoufoxUnavailable, scrape_page

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_TTL_S = 1800  # 30 phút cache cho kết quả khảo sát thị trường
_cache: dict[str, tuple[float, list[StoreCandidate]]] = {}

_PRICE_RE = re.compile(r"([\d.,]+)\s*(?:đ|k|vnd)?", re.IGNORECASE)


def parse_price(val: Any) -> int:
    """Chuyển đổi giá tiền từ mọi định dạng (int, "35.000đ", "35k", "35,000") về int VNĐ."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().lower()
    if not s:
        return 0

    # Trường hợp viết tắt 35k -> 35000
    if s.endswith("k"):
        num_str = s[:-1].strip().replace(",", ".")
        try:
            return int(float(num_str) * 1000)
        except ValueError:
            pass

    # Trường hợp định dạng tiền tệ "35.000đ" hoặc "35,000"
    m = _PRICE_RE.search(s)
    if not m:
        return 0

    clean_num = m.group(1).replace(".", "").replace(",", "")
    try:
        return int(clean_num)
    except ValueError:
        return 0


def _get_cache_ttl_s() -> int:
    try:
        return max(60, int(os.getenv("CA_DELIVERY_CACHE_TTL_S", str(_DEFAULT_CACHE_TTL_S))))
    except ValueError:
        return _DEFAULT_CACHE_TTL_S


def _cache_key(lat: float, lng: float, keyword: str, radius_km: float) -> str:
    return f"delivery:{round(lat, 3)}:{round(lng, 3)}:{(keyword or '').strip().lower()}:{round(radius_km, 1)}"


def _cache_get(key: str) -> list[StoreCandidate] | None:
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is None:
        return None
    cached_at, items = hit
    if now - cached_at > _get_cache_ttl_s():
        _cache.pop(key, None)
        return None
    return items


def _cache_put(key: str, items: list[StoreCandidate]) -> None:
    _cache[key] = (time.monotonic(), items)


def _reset_cache() -> None:
    """Xóa cache bộ nhớ (dùng cho test)."""
    _cache.clear()


def extract_delivery_stores_from_json(payload: dict[str, Any]) -> list[StoreCandidate]:
    """Trích xuất danh sách quán và menu từ payload JSON của ShopeeFood/Delivery API.

    Hàm thuần (pure function) — dễ dàng kiểm thử bằng JSON fixture tĩnh.
    """
    stores: list[StoreCandidate] = []
    if not isinstance(payload, dict):
        return stores

    # Xử lý các cấu trúc payload phổ biến của ShopeeFood / Foody
    raw_restaurants = (
        payload.get("restaurants")
        or payload.get("reply", {}).get("restaurants")
        or payload.get("data", {}).get("restaurants")
        or payload.get("items")
        or []
    )

    for item in raw_restaurants:
        if not isinstance(item, dict):
            continue

        store_id = str(item.get("id") or item.get("restaurant_id") or "")
        name = str(item.get("name") or item.get("restaurant_name") or "").strip()
        if not name:
            continue

        address = str(item.get("address") or item.get("short_address") or "").strip()
        url = str(item.get("url") or item.get("share_url") or "")

        # Rating: thang 5.0
        rating_raw = item.get("rating") or item.get("avg_rating") or item.get("star") or 0.0
        try:
            rating = round(float(rating_raw), 1)
        except (ValueError, TypeError):
            rating = 0.0

        # Review count / Total reviews
        review_count_raw = (
            item.get("review_count")
            or item.get("rating_count")
            or item.get("total_rating")
            or item.get("total_reviews")
            or 0
        )
        try:
            review_count = int(review_count_raw)
        except (ValueError, TypeError):
            review_count = 0

        # Huy hiệu Quán yêu thích / Đối tác
        is_favorite = bool(
            item.get("is_favorite")
            or item.get("is_quality_merchant")
            or item.get("is_official")
            or "quán yêu thích" in str(item.get("badges", "")).lower()
        )

        # Distance km
        dist_raw = item.get("distance_km") or item.get("distance") or 0.0
        try:
            distance_km = round(float(dist_raw), 2)
        except (ValueError, TypeError):
            distance_km = 0.0

        sold_text = str(item.get("sold_count_text") or item.get("total_order") or "")

        # Trích xuất danh sách món
        dishes: list[DishItem] = []
        raw_dishes = (
            item.get("dishes")
            or item.get("menu_items")
            or item.get("catalogues")
            or []
        )

        for d in raw_dishes:
            if not isinstance(d, dict):
                continue
            dish_name = str(d.get("name") or d.get("dish_name") or "").strip()
            dish_price = parse_price(d.get("price") or d.get("price_vnd") or 0)
            if not dish_name or dish_price <= 0:
                continue

            is_bestseller = bool(
                d.get("is_bestseller")
                or d.get("is_best_seller")
                or d.get("is_signature")
                or "bán chạy" in dish_name.lower()
                or "hot" in dish_name.lower()
            )
            cat = str(d.get("category") or d.get("category_name") or "")

            dishes.append(
                DishItem(
                    name=dish_name,
                    price=dish_price,
                    is_bestseller=is_bestseller,
                    category=cat,
                )
            )

        stores.append(
            StoreCandidate(
                id=store_id,
                name=name,
                address=address,
                distance_km=distance_km,
                rating=rating,
                review_count=review_count,
                is_favorite=is_favorite,
                sold_count_text=sold_text,
                url=url,
                dishes=dishes,
            )
        )

    return stores


def fetch_shopeefood_page(
    page: Any,
    keyword: str,
    lat: float,
    lng: float,
    radius_km: float = 5.0,
) -> dict[str, Any]:
    """Điều hướng trang ShopeeFood với tọa độ chỉ định và bắt response API."""
    captured_payloads: list[dict[str, Any]] = []

    def on_response(response: Any) -> None:
        url = response.url
        # Bắt các API search / browse quán của ShopeeFood
        if "api/delivery/get_browse_dishes" in url or "api/delivery/search" in url:
            try:
                data = response.json()
                if isinstance(data, dict):
                    captured_payloads.append(data)
            except Exception:
                pass

    try:
        page.on("response", on_response)
        # Giả lập vị trí địa lý Geolocation trên browser context
        page.context.set_geolocation({"latitude": lat, "longitude": lng})
        search_url = f"https://shopeefood.vn/search?keyword={keyword}"
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        time.sleep(3.0)  # Chờ SPA nạp danh sách quán
    except Exception as exc:
        logger.warning("Lỗi trong quá trình fetch_shopeefood_page: %s", exc)
    finally:
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    if captured_payloads:
        return captured_payloads[0]
    return {}


def scrape_delivery_stores_camoufox(
    latitude: float,
    longitude: float,
    keyword: str,
    radius_km: float = 5.0,
) -> list[StoreCandidate]:
    """Hàm điều phối cào danh sách quán qua Camoufox có cache."""
    cache_k = _cache_key(latitude, longitude, keyword, radius_km)
    cached = _cache_get(cache_k)
    if cached is not None:
        logger.info("Delivery Camoufox cache hit cho key=%s", cache_k)
        return cached

    def _extractor(page: Any) -> dict[str, Any]:
        return fetch_shopeefood_page(
            page=page,
            keyword=keyword,
            lat=latitude,
            lng=longitude,
            radius_km=radius_km,
        )

    target_url = f"https://shopeefood.vn/search?keyword={keyword}"
    try:
        result_json = scrape_page(target_url, _extractor)
    except CamoufoxUnavailable:
        logger.info("Camoufox không khả dụng cho delivery scraping")
        raise
    except Exception as exc:
        logger.warning("Scrape delivery thất bại: %s", exc)
        return []

    stores = extract_delivery_stores_from_json(result_json)
    if stores:
        _cache_put(cache_k, stores)
    return stores
