"""ShopeeFood v2 parser — tách original_price_vnd và effective_price_vnd.

Plan mục 1.5.2: ShopeeFood phần lớn hiển thị GIÁ ĐÃ KHUYẾN MÃI. Nếu lấy giá đó
làm mẫu tính AMBI thì chỉ số bị kéo thấp giả tạo. Parser này tách rõ 2 loại giá
NGAY TẠI TẦNG PARSE, không gộp chung rồi tính lại sau.

ADR-002: hàm thuần, không LLM, không network, không đọc file.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ca_contracts.catchment_survey_v2 import ChannelMode, ConfidenceLevel, MenuItemPrice

from ca_agents.sources.delivery_camoufox_source import parse_price
from ca_agents.sources.dish_name_normalizer import normalize_dish_name

logger = logging.getLogger(__name__)

# Regex bắt giá gốc bị gạch ngang (strikethrough price)
# VD: "45.000đ" trong field original_price, hoặc text có gạch ngang
_STRIKETHROUGH_RE = re.compile(
    r"(?:original|list|base|strike|before|was)\s*[_-]?price",
    re.IGNORECASE,
)

# Regex bắt giá khuyến mãi
_PROMO_RE = re.compile(
    r"(?:sale|discount|promo|deal|flash|special)\s*[_-]?price",
    re.IGNORECASE,
)

# Regex bắt phần trăm giảm giá
_DISCOUNT_PCT_RE = re.compile(r"(\d{1,2})\s*%")


def _extract_price_pair(dish_data: dict[str, Any]) -> tuple[int | None, int, bool]:
    """Tách cặp giá (original, effective) từ dữ liệu món.

    Returns:
        (original_price_vnd, effective_price_vnd, is_promotional)

    Logic:
    - Nếu JSON có field riêng cho giá gốc và giá sale → dùng trực tiếp
    - Nếu chỉ có 1 giá → original = effective, is_promotional = False
    - Nếu có discount_pct → suy ngược original từ effective
    - Nếu không tách được → log warning, original = effective
    """
    # Tìm giá gốc (original/list/base price)
    original_raw = None
    for key in dish_data:
        if _STRIKETHROUGH_RE.search(str(key)):
            original_raw = dish_data[key]
            break

    # Tìm giá khuyến mãi (sale/discount/promo price)
    effective_raw = None
    for key in dish_data:
        if _PROMO_RE.search(str(key)):
            effective_raw = dish_data[key]
            break

    # Fallback: các field phổ biến
    if original_raw is None:
        original_raw = (
            dish_data.get("original_price")
            or dish_data.get("list_price")
            or dish_data.get("base_price")
            or dish_data.get("price_before_discount")
        )

    if effective_raw is None:
        effective_raw = (
            dish_data.get("sale_price")
            or dish_data.get("discount_price")
            or dish_data.get("promo_price")
            or dish_data.get("price")
            or dish_data.get("price_vnd")
        )

    original_vnd = parse_price(original_raw) if original_raw is not None else 0
    effective_vnd = parse_price(effective_raw) if effective_raw is not None else 0

    # Kiểm tra discount percentage
    discount_text = str(
        dish_data.get("discount_pct")
        or dish_data.get("discount_percent")
        or dish_data.get("discount")
        or ""
    )
    discount_match = _DISCOUNT_PCT_RE.search(discount_text)
    discount_pct = int(discount_match.group(1)) if discount_match else 0

    is_promotional = False

    # Case 1: Có cả 2 giá khác nhau → khuyến mãi thật
    if original_vnd > 0 and effective_vnd > 0 and original_vnd != effective_vnd:
        is_promotional = True
        return original_vnd, effective_vnd, is_promotional

    # Case 2: Chỉ có effective + discount_pct → suy ngược original
    if effective_vnd > 0 and discount_pct > 0 and original_vnd <= 0:
        original_vnd = int(effective_vnd / (1 - discount_pct / 100))
        is_promotional = True
        return original_vnd, effective_vnd, is_promotional

    # Case 3: Chỉ có 1 giá → không khuyến mãi
    if effective_vnd > 0 and original_vnd <= 0:
        return effective_vnd, effective_vnd, False

    if original_vnd > 0 and effective_vnd <= 0:
        return original_vnd, original_vnd, False

    # Case 4: Không có giá nào
    return None, 0, False


def extract_menu_items_v2(
    payload: dict[str, Any],
    *,
    source_channel: ChannelMode = ChannelMode.DELIVERY_PLATFORM,
) -> list[MenuItemPrice]:
    """Trích xuất MenuItemPrice v2 từ payload JSON ShopeeFood.

    Tách rõ original_price_vnd và effective_price_vnd ngay tại tầng parse.
    Log warning khi không tách được 2 giá.

    Args:
        payload: JSON response từ ShopeeFood API
        source_channel: kênh nguồn (delivery_platform / dine_in_vision)

    Returns:
        Danh sách MenuItemPrice với giá đã tách riêng
    """
    items: list[MenuItemPrice] = []
    if not isinstance(payload, dict):
        return items

    # Tìm danh sách món trong payload
    raw_dishes = (
        payload.get("dishes")
        or payload.get("menu_items")
        or payload.get("catalogues")
        or payload.get("items")
        or []
    )

    for dish_data in raw_dishes:
        if not isinstance(dish_data, dict):
            continue

        raw_name = str(
            dish_data.get("name") or dish_data.get("dish_name") or ""
        ).strip()
        if not raw_name:
            continue

        original_vnd, effective_vnd, is_promotional = _extract_price_pair(dish_data)

        if effective_vnd <= 0:
            continue

        # Log warning khi không tách được giá
        if original_vnd is not None and original_vnd == effective_vnd and is_promotional is False:
            # Chỉ log nếu có dấu hiệu khuyến mãi nhưng không tách được
            has_discount_signal = any(
                k in dish_data
                for k in ("discount", "discount_pct", "sale_price", "promo_price")
            )
            if has_discount_signal:
                logger.warning(
                    "ShopeeFood: không tách được original/effective cho món '%s' "
                    "(có tín hiệu khuyến mãi nhưng giá trùng nhau)",
                    raw_name,
                )

        # Chuẩn hoá tên món
        normalized_name = normalize_dish_name(raw_name)

        # Phát hiện combo
        is_combo = bool(
            dish_data.get("is_combo")
            or dish_data.get("is_set")
            or "combo" in raw_name.lower()
            or "set" in raw_name.lower()
        )

        # Ghi chú khẩu phần
        portion_note = str(
            dish_data.get("portion")
            or dish_data.get("size")
            or dish_data.get("portion_note")
            or ""
        ).strip() or None

        # Confidence: cao nếu có cả 2 giá, trung bình nếu chỉ 1 giá.
        # Khai báo kiểu Literal tường minh: không có nó mypy suy ra `str` và contract
        # `MenuItemPrice.confidence: ConfidenceLevel` sẽ từ chối.
        confidence: ConfidenceLevel = (
            "high" if (original_vnd and original_vnd != effective_vnd) else "medium"
        )

        # is_fallback_derived: True nếu suy ngược từ discount_pct
        is_fallback = (
            original_vnd is not None
            and original_vnd > effective_vnd
            and not any(
                k in dish_data
                for k in ("original_price", "list_price", "base_price", "price_before_discount")
            )
        )

        items.append(
            MenuItemPrice(
                item_name_raw=raw_name,
                item_name_normalized=normalized_name,
                original_price_vnd=original_vnd,
                effective_price_vnd=effective_vnd,
                is_promotional=is_promotional,
                is_combo=is_combo,
                portion_note=portion_note,
                source_channel=source_channel,
                confidence=confidence,
                is_fallback_derived=is_fallback,
            )
        )

    return items


def extract_stores_menu_items_v2(
    payload: dict[str, Any],
) -> dict[str, list[MenuItemPrice]]:
    """Trích xuất menu items theo từng quán từ payload ShopeeFood.

    Returns:
        Dict mapping store_id → list[MenuItemPrice]
    """
    result: dict[str, list[MenuItemPrice]] = {}
    if not isinstance(payload, dict):
        return result

    raw_restaurants = (
        payload.get("restaurants")
        or payload.get("reply", {}).get("restaurants")
        or payload.get("data", {}).get("restaurants")
        or payload.get("items")
        or []
    )

    for restaurant in raw_restaurants:
        if not isinstance(restaurant, dict):
            continue

        store_id = str(
            restaurant.get("id") or restaurant.get("restaurant_id") or ""
        )
        if not store_id:
            continue

        items = extract_menu_items_v2(restaurant)
        if items:
            result[store_id] = items

    return result
