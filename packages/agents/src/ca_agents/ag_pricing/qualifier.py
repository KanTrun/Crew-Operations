"""Bộ lọc kép (Dual-Gate) và thống kê Bayes cho khảo sát giá đối thủ F&B.

ADR-002: Hoàn toàn tất định (deterministic), không dùng LLM để tính toán số liệu.
"""

from __future__ import annotations

from typing import Any

from ca_contracts.catchment_survey import (
    DishItem,
    PriceDistribution,
    StoreCandidate,
    ValidatedStore,
)


def calculate_bayesian_rating(
    review_count: int,
    rating: float,
    m: int = 50,
    prior_c: float = 4.2,
) -> float:
    """Tính điểm đánh giá Bayes (Bayesian Weighted Rating) theo chuẩn IMDB.

    Công thức: WR = (v / (v + m)) * R + (m / (v + m)) * C
    - v (review_count): số lượng đánh giá thực tế
    - R (rating): điểm đánh giá trung bình của quán
    - m: ngưỡng đánh giá tối thiểu để có trọng số đầy đủ (mặc định 50)
    - C (prior_c): điểm đánh giá trung bình của toàn bộ thị trường (mặc định 4.2)
    """
    v = max(0, review_count)
    r = max(1.0, min(5.0, float(rating)))

    if v + m == 0:
        return prior_c

    wr = (v / (v + m)) * r + (m / (v + m)) * prior_c
    return round(max(1.0, min(5.0, wr)), 2)


def calculate_distance_decay_weight(
    distance_km: float,
    alpha: float = 0.15,
) -> float:
    """Tính hệ số suy giảm trọng số theo khoảng cách địa lý.

    Công thức: W_dist = 1 / (1 + alpha * d)
    Quán ở cự ly gần cạnh tranh trực tiếp hơn, quán ở rìa 5-7km có trọng số nhỏ hơn.
    """
    d = max(0.0, float(distance_km))
    weight = 1.0 / (1.0 + alpha * d)
    return round(weight, 4)


def qualify_stores(
    stores: list[StoreCandidate],
    min_reviews: int = 50,
    min_rating: float = 4.2,
    prior_c: float = 4.2,
    m: int = 50,
) -> tuple[list[ValidatedStore], list[dict[str, Any]]]:
    """Lọc kép (Dual-Gate) xác thực các quán có bằng chứng thị trường (Market-Validated).

    Gate 1 (Volume): Đủ số lượng review để chứng minh có lượng khách mua thật.
    Gate 2 (Quality): Điểm đánh giá gốc >= min_rating VÀ điểm Bayes >= 4.0.

    Returns:
        tuple[list[ValidatedStore], list[dict[str, Any]]]
        - validated_stores: danh sách quán vượt qua bộ lọc
        - disqualified_records: danh sách quán bị loại kèm lý do cụ thể
    """
    validated: list[ValidatedStore] = []
    disqualified: list[dict[str, Any]] = []

    for store in stores:
        # Gate 1: Volume check
        has_volume = store.review_count >= min_reviews
        if not has_volume and store.is_favorite and store.review_count >= max(20, min_reviews // 2):
            # Ưu đãi đặc xá cho quán có danh hiệu 'Quán yêu thích' chính thức
            has_volume = True

        if not has_volume:
            disqualified.append({
                "store_id": store.id,
                "store_name": store.name,
                "reason": "khong_dat_nguong_luot_danh_gia",
                "review_count": store.review_count,
                "threshold": min_reviews,
            })
            continue

        # Gate 2: Quality check
        bayesian_r = calculate_bayesian_rating(
            review_count=store.review_count,
            rating=store.rating,
            m=m,
            prior_c=prior_c,
        )

        if store.rating < min_rating:
            disqualified.append({
                "store_id": store.id,
                "store_name": store.name,
                "reason": "diem_danh_gia_goc_thap",
                "rating": store.rating,
                "threshold": min_rating,
            })
            continue

        if bayesian_r < 4.0:
            disqualified.append({
                "store_id": store.id,
                "store_name": store.name,
                "reason": "diem_bayes_chua_dat_chuan_tin_cay",
                "bayesian_rating": bayesian_r,
                "threshold": 4.0,
            })
            continue

        # Đạt cả 2 Gate
        dist_weight = calculate_distance_decay_weight(store.distance_km)
        validated.append(
            ValidatedStore(
                id=store.id,
                name=store.name,
                address=store.address,
                distance_km=store.distance_km,
                rating=store.rating,
                review_count=store.review_count,
                bayesian_rating=bayesian_r,
                distance_weight=dist_weight,
                is_favorite=store.is_favorite,
                url=store.url,
            )
        )

    # Sắp xếp các quán đạt chuẩn theo điểm tổng hợp (Bayesian Rating * Distance Weight)
    validated.sort(
        key=lambda s: s.bayesian_rating * s.distance_weight,
        reverse=True,
    )
    return validated, disqualified


def compute_weighted_percentile(
    values: list[int],
    weights: list[float],
    percentile: float,
) -> int:
    """Tính phân vị có trọng số (Weighted Percentile) bằng toán thuần túy."""
    if not values:
        return 0
    if len(values) == 1:
        return values[0]

    pairs = sorted(zip(values, weights, strict=True), key=lambda x: x[0])
    total_weight = sum(weights)
    if total_weight <= 0:
        return pairs[0][0]

    target = (percentile / 100.0) * total_weight
    cumulative = 0.0
    for val, w in pairs:
        cumulative += w
        if cumulative >= target:
            return val
    return pairs[-1][0]


def compute_price_distribution(
    dishes_with_weights: list[tuple[DishItem, float]],
) -> PriceDistribution:
    """Tính toán toàn bộ thống kê phân bố giá từ tập mẫu món ăn có trọng số."""
    if not dishes_with_weights:
        return PriceDistribution(
            sample_size=0,
            min_price=0,
            max_price=0,
            median_price=0,
            p25_price=0,
            p75_price=0,
            volume_weighted_mean=0,
            sweet_spot_range=[0, 0],
        )

    # Lọc các món có giá hợp lệ (> 0 và < 2.000.000 VNĐ để loại trừ outlier nhập lỗi)
    valid_pairs = [
        (d, max(0.001, w))
        for d, w in dishes_with_weights
        if 5000 <= d.price <= 1000000
    ]

    if not valid_pairs:
        return PriceDistribution(
            sample_size=0,
            min_price=0,
            max_price=0,
            median_price=0,
            p25_price=0,
            p75_price=0,
            volume_weighted_mean=0,
            sweet_spot_range=[0, 0],
        )

    prices = [d.price for d, _ in valid_pairs]
    weights = [w for _, w in valid_pairs]

    min_price = min(prices)
    max_price = max(prices)

    p25 = compute_weighted_percentile(prices, weights, 25.0)
    p50 = compute_weighted_percentile(prices, weights, 50.0)
    p75 = compute_weighted_percentile(prices, weights, 75.0)

    total_w = sum(weights)
    weighted_mean = int(round(sum(p * w for p, w in zip(prices, weights, strict=True)) / total_w))

    # Làm tròn đến 1.000 VNĐ cho thực tế thị trường F&B Việt Nam
    p25_rounded = int(round(p25 / 1000.0) * 1000)
    p50_rounded = int(round(p50 / 1000.0) * 1000)
    p75_rounded = int(round(p75 / 1000.0) * 1000)
    weighted_mean_rounded = int(round(weighted_mean / 1000.0) * 1000)

    sweet_spot = [p25_rounded, p75_rounded]

    return PriceDistribution(
        sample_size=len(valid_pairs),
        min_price=min_price,
        max_price=max_price,
        median_price=p50_rounded,
        p25_price=p25_rounded,
        p75_price=p75_rounded,
        volume_weighted_mean=weighted_mean_rounded,
        sweet_spot_range=sweet_spot,
    )
