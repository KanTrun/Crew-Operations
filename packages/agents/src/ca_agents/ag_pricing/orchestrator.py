"""Điều phối khảo sát giá và định vị thị trường F&B (Catchment Price Radar).

Tuân thủ:
- ADR-002: Thống kê tất định, template phân tích kinh tế rõ ràng.
- ADR-008: Phân tích khách quan dựa trên dữ liệu thật, chủ quán là người quyết định.
- Hỗ trợ: Kênh bán Online vs Tại Chỗ (Dine-in) & Ma trận món thay thế (Share of Stomach).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ca_contracts.catchment_survey import (
    CatchmentSurveyRequest,
    CatchmentSurveyResponse,
    DishItem,
    MenuSnapshot,
    PriceDistribution,
    StoreCandidate,
    SubstituteCategoryStats,
    SubstitutePriceComparison,
    TopCompetitorSignature,
    ValidatedStore,
)

from ca_agents.ag_pricing.qualifier import (
    compute_price_distribution,
    qualify_stores,
)
from ca_agents.ag_pricing.substitute_matrix import (
    calculate_substitute_stats,
    classify_dish_category,
    compute_area_meal_budget_index,
    get_substitute_categories,
)
from ca_agents.clients.camoufox_client import CamoufoxUnavailable
from ca_agents.sources.delivery_camoufox_source import scrape_delivery_stores_camoufox
from ca_agents.sources.gmaps_menu_source import scrape_gmaps_menu_images_camoufox
from ca_agents.sources.gmaps_serpapi_source import fetch_gmaps_competitors_serpapi

logger = logging.getLogger(__name__)


def generate_market_insight(
    category: str,
    radius_km: float,
    channel_mode: str,
    validated_stores: list[ValidatedStore],
    price_dist: PriceDistribution,
    top_signatures: list[TopCompetitorSignature],
    substitute_comp: SubstitutePriceComparison | None = None,
) -> str:
    """Tạo nhận định thị trường định lượng, khách quan và có tính hành động cao."""
    if not validated_stores or price_dist.sample_size == 0:
        return (
            f"Chưa đủ dữ liệu khảo sát trong bán kính {radius_km}km cho ngành hàng '{category}'. "
            "Khu vực này hiện có ít đối thủ lớn đạt ngưỡng kiểm chứng thị trường. "
            "Quán có thể cân nhắc khảo sát với bán kính rộng hơn (ví dụ 5km - 7km) hoặc hạ nhẹ ngưỡng lọc review."
        )

    channel_desc = "Tại Quán (Dine-in)" if channel_mode == "dine_in_vision" else "Trên Sàn Delivery"
    p25_k = f"{price_dist.p25_price:,.0f}đ".replace(",", ".")
    p50_k = f"{price_dist.median_price:,.0f}đ".replace(",", ".")
    p75_k = f"{price_dist.p75_price:,.0f}đ".replace(",", ".")
    sweet_min_k = f"{price_dist.sweet_spot_range[0]:,.0f}đ".replace(",", ".")
    sweet_max_k = f"{price_dist.sweet_spot_range[1]:,.0f}đ".replace(",", ".")
    weighted_mean_k = f"{price_dist.volume_weighted_mean:,.0f}đ".replace(",", ".")

    top_names = ", ".join([f"'{s.name}' ({s.rating}★/{s.review_count} reviews)" for s in validated_stores[:3]])

    lines = [
        f"### 📊 Báo cáo định vị giá — Ngành '{category.capitalize()}' [{channel_desc}] (Bán kính {radius_km}km)",
        f"- **Độ phủ thị trường:** Phát hiện **{len(validated_stores)} đối thủ mạnh** đã được thị trường kiểm chứng (Top đầu: {top_names}).",
        f"- **Mức sẵn sàng chi trả (WTP):** Giá trung bình có trọng số lượt bán là **{weighted_mean_k}** (dựa trên {price_dist.sample_size} món ăn hợp lệ).",
        "- **Phân khúc thị trường khu vực:**",
        f"  • *Phổ thông / Dễ tiếp cận (< P25):* Dưới {p25_k}.",
        f"  • *Vùng giá vàng / Bán chạy nhất (Sweet Spot P25 - P75):* **{sweet_min_k} – {sweet_max_k}** (Trung vị thị trường: **{p50_k}**).",
        f"  • *Phân khúc cao cấp / Đòi hỏi trải nghiệm (> P75):* Trên {p75_k}.",
    ]

    # Nếu có phân tích món thay thế (Share of Stomach)
    if substitute_comp and substitute_comp.substitute_categories:
        ambi_k = f"{substitute_comp.area_meal_budget_index:,.0f}đ".replace(",", ".")
        sub_details = []
        for s in substitute_comp.substitute_categories:
            sub_median_k = f"{s.median_price:,.0f}đ".replace(",", ".")
            sub_details.append(f"{s.category_name.capitalize()} (Trung vị: {sub_median_k})")

        lines.extend([
            "- **🍽️ Áp lực cạnh tranh liên ngành (Share of Stomach):**",
            f"  • *Các món thay thế xung quanh:* {', '.join(sub_details)}.",
            f"  • *Trần ngân sách bữa ăn khu vực (AMBI):* **{ambi_k} / suất**.",
        ])

        # Nhận định chiến lược đối chiếu
        if price_dist.median_price > substitute_comp.area_meal_budget_index:
            diff_k = f"{price_dist.median_price - substitute_comp.area_meal_budget_index:,.0f}đ".replace(",", ".")
            lines.append(
                f"  • *Cảnh báo định giá:* Món chính '{category}' đang cao hơn trần ngân sách bữa ăn khu vực {diff_k}. "
                "Quán cần chú trọng không gian máy lạnh hoặc tặng kèm trà đá để khách không bỏ sang các món thay thế lân cận."
            )
        else:
            lines.append(
                f"  • *Lợi thế cạnh tranh:* Món chính '{category}' đang nằm vừa vặn trong trần ngân sách khu vực ({ambi_k}), rất có ưu thế hút khách trưa."
            )

    lines.extend([
        "- **💡 Khuyến nghị chiến lược cho quán:**",
        f"  1. **Món chủ đạo (Signature):** Nên định vị ở mức **{p50_k}** (hoặc trong khoảng **{sweet_min_k} – {p50_k}**).",
        f"  2. **Combo / Upsell:** Thiết lập gói combo kèm đồ uống ở mức **{sweet_max_k} – {p75_k}**.",
    ])
    if channel_mode == "dine_in_vision":
        delivery_equiv_k = f"{int(round(price_dist.median_price * 1.25 / 1000.0) * 1000):,.0f}đ".replace(",", ".")
        lines.append(
            f"  3. **Nếu mở bán online:** Đề xuất niêm yết trên ShopeeFood ở mức **{delivery_equiv_k}** (đã bù phí sàn 20-25%)."
        )

    return "\n".join(lines)


def run_catchment_price_survey(
    request: CatchmentSurveyRequest,
    store_fetcher: Callable[[float, float, str, float], list[StoreCandidate]] | None = None,
) -> CatchmentSurveyResponse:
    """Thực thi cuộc khảo sát giá đối thủ trong bán kính theo yêu cầu.

    Args:
        request: Tham số yêu cầu khảo sát
        store_fetcher: Provider lấy danh sách quán (mặc định cào live, có thể inject mock cho test)
    """
    if store_fetcher is not None:
        fetcher = store_fetcher
    elif request.channel_mode == "dine_in_vision":
        def _dine_in_fetcher(lat: float, lng: float, kw: str, r: float) -> list[StoreCandidate]:
            try:
                candidates = fetch_gmaps_competitors_serpapi(lat, lng, kw, r)
                if candidates:
                    return candidates
            except Exception as exc:
                logger.info("SerpApi không khả dụng (%s), chuyển fallback Camoufox Google Maps", exc)

            try:
                return scrape_gmaps_menu_images_camoufox(lat, lng, kw, r)
            except Exception as cam_exc:
                logger.warning("Camoufox Google Maps thất bại (%s), thử lấy stale cache", cam_exc)
                try:
                    from ca_agents.clients.serpapi_client import get_stale_cache_payload
                    from ca_agents.sources.gmaps_serpapi_source import (
                        parse_gmaps_results_to_candidates,
                    )

                    zoom = 15 if r <= 3.0 else (14 if r <= 7.0 else 13)
                    stale_params = {
                        "q": kw.strip() or "quán cà phê",
                        "ll": f"@{lat},{lng},{zoom}z",
                        "hl": "vi",
                        "gl": "vn",
                        "type": "search",
                    }
                    stale_json = get_stale_cache_payload("google_maps", stale_params)
                    if stale_json:
                        return parse_gmaps_results_to_candidates(
                            stale_json, lat, lng, r, data_source="cache"
                        )
                except Exception as stale_exc:
                    logger.debug("Không đọc được stale cache: %s", stale_exc)
                return []

        fetcher = _dine_in_fetcher
    else:
        fetcher = scrape_delivery_stores_camoufox

    try:
        raw_stores = fetcher(
            request.latitude,
            request.longitude,
            request.category_keyword,
            request.radius_km,
        )
    except CamoufoxUnavailable:
        logger.warning("Camoufox không khả dụng, không thể cào live")
        raw_stores = []
    except Exception as exc:
        logger.error("Lỗi khi fetch stores: %s", exc)
        raw_stores = []

    # Lọc kép (Dual-Gate)
    validated_stores, disqualified = qualify_stores(
        stores=raw_stores,
        min_reviews=request.min_reviews,
        min_rating=request.min_rating,
    )

    # Khởi tạo danh sách theo dõi
    dishes_with_weights: list[tuple[DishItem, float]] = []
    substitute_dishes_map: dict[str, list[DishItem]] = {}
    top_signatures: list[TopCompetitorSignature] = []
    menu_snapshots: list[MenuSnapshot] = []

    # Danh mục thay thế cần theo dõi nếu bật include_substitutes
    target_subs = get_substitute_categories(request.category_keyword) if request.include_substitutes else []

    # Mapping store_id -> store_candidate để lấy menu
    raw_map = {s.id: s for s in raw_stores}

    for val_store in validated_stores:
        raw_store = raw_map.get(val_store.id)
        if not raw_store:
            continue

        store_weight = val_store.bayesian_rating * val_store.distance_weight
        store_dishes = raw_store.dishes

        # Nếu đang ở chế độ Dine-in (Tại chỗ) và món chưa có giá OCR:
        # Áp dụng thuật toán Reverse Markup (-20% phí sàn) làm fallback
        adjusted_dishes: list[DishItem] = []
        for d in store_dishes:
            price = d.price
            source_t = d.source_type
            if request.channel_mode == "dine_in_vision" and d.source_type != "dine_in_ocr":
                # Trừ 20% phí sàn, làm tròn đến 1.000 VNĐ
                price = int(round((price * 0.80) / 1000.0) * 1000)
                source_t = "dine_in_estimated"

            adjusted_dishes.append(
                DishItem(
                    name=d.name,
                    price=price,
                    is_bestseller=d.is_bestseller,
                    category=d.category,
                    source_type=source_t,
                )
            )

        # Lưu snapshot ảnh menu nếu có
        if raw_store.menu_image_urls:
            val_store.has_menu_images = True
            for img_url in raw_store.menu_image_urls[:request.max_menu_images_per_store]:
                menu_snapshots.append(
                    MenuSnapshot(
                        store_id=val_store.id,
                        store_name=val_store.name,
                        image_url=img_url,
                        source="google_maps",
                        extracted_dishes_count=len(adjusted_dishes),
                    )
                )

        # Lọc danh sách món phân tích
        selected_dishes = [d for d in adjusted_dishes if d.is_bestseller] if request.only_bestsellers else adjusted_dishes
        if not selected_dishes:
            selected_dishes = adjusted_dishes

        for dish in selected_dishes:
            cat_type = classify_dish_category(dish.name, request.category_keyword)
            if cat_type == "core":
                dishes_with_weights.append((dish, store_weight))
            elif request.include_substitutes and cat_type in target_subs:
                substitute_dishes_map.setdefault(cat_type, []).append(dish)
            else:
                # Nếu không khớp cụ thể nhưng là món ăn chính của quán core, vẫn tính vào core
                dishes_with_weights.append((dish, store_weight))

        # Lưu món signature đại diện cho đối thủ top đầu
        best_dish = next((d for d in adjusted_dishes if d.is_bestseller), None) or (adjusted_dishes[0] if adjusted_dishes else None)
        if best_dish:
            top_signatures.append(
                TopCompetitorSignature(
                    store_name=val_store.name,
                    dish_name=best_dish.name,
                    price=best_dish.price,
                    is_bestseller=best_dish.is_bestseller,
                    category=best_dish.category,
                )
            )

    # Tính toán phân bố giá món chính
    price_dist = compute_price_distribution(dishes_with_weights)

    # Xử lý ma trận món thay thế (Share of Stomach)
    substitute_comp: SubstitutePriceComparison | None = None
    if request.include_substitutes:
        sub_stats_list: list[SubstituteCategoryStats] = []
        for sub_name, s_dishes in substitute_dishes_map.items():
            stat = calculate_substitute_stats(sub_name, s_dishes)
            if stat:
                sub_stats_list.append(stat)

        ambi = compute_area_meal_budget_index(price_dist, sub_stats_list)
        substitute_comp = SubstitutePriceComparison(
            core_category_name=request.category_keyword,
            core_price_distribution=price_dist,
            substitute_categories=sub_stats_list,
            area_meal_budget_index=ambi,
        )

    # Sinh nhận định thị trường định lượng
    insight = generate_market_insight(
        category=request.category_keyword,
        radius_km=request.radius_km,
        channel_mode=request.channel_mode,
        validated_stores=validated_stores,
        price_dist=price_dist,
        top_signatures=top_signatures,
        substitute_comp=substitute_comp,
    )

    return CatchmentSurveyResponse(
        request=request,
        total_scanned_stores=len(raw_stores),
        validated_stores_count=len(validated_stores),
        disqualified_stores_count=len(disqualified),
        validated_stores=validated_stores,
        price_distribution=price_dist,
        top_competitor_signatures=top_signatures[:10],
        substitute_comparison=substitute_comp,
        menu_snapshots=menu_snapshots,
        market_insight=insight,
    )
