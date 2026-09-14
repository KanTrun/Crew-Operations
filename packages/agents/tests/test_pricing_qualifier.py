"""Kiểm thử unit test cho thuật toán lọc kép Dual-Gate và thống kê Bayes (AG-PRICING)."""

from __future__ import annotations

import json
from pathlib import Path

from ca_agents.ag_pricing.qualifier import (
    calculate_bayesian_rating,
    calculate_distance_decay_weight,
    compute_price_distribution,
    compute_weighted_percentile,
    qualify_stores,
)
from ca_agents.sources.delivery_camoufox_source import extract_delivery_stores_from_json
from ca_contracts.catchment_survey import DishItem

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "delivery_stores_sample.json"


def test_bayesian_rating_prevents_small_sample_bias() -> None:
    """Quán có 2 review 5.0★ phải bị kéo về gần giá trị kỳ vọng thị trường (4.2★)."""
    rating_small = calculate_bayesian_rating(review_count=2, rating=5.0, m=50, prior_c=4.2)
    # (2/52)*5.0 + (50/52)*4.2 = 0.192 + 4.038 = 4.23
    assert rating_small < 4.3
    assert rating_small >= 4.2

    # Quán có 2000 review 4.8★ phải giữ nguyên độ uy tín cao
    rating_large = calculate_bayesian_rating(review_count=2000, rating=4.8, m=50, prior_c=4.2)
    # (2000/2050)*4.8 + (50/2050)*4.2 = 4.68 + 0.10 = 4.79
    assert rating_large >= 4.78


def test_distance_decay_weight() -> None:
    w0 = calculate_distance_decay_weight(0.0)
    w1 = calculate_distance_decay_weight(1.0)
    w5 = calculate_distance_decay_weight(5.0)

    assert w0 == 1.0
    assert w1 < w0
    assert w5 < w1
    assert w5 > 0.0


def test_dual_gate_filters_zombie_and_bad_rating_stores() -> None:
    """Kiểm tra bộ lọc kép lọc sạch quán ảo và quán đánh giá thấp từ fixture."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    stores = extract_delivery_stores_from_json(data)
    assert len(stores) == 6

    validated, disqualified = qualify_stores(
        stores=stores,
        min_reviews=50,
        min_rating=4.2,
    )

    # Chỉ 3 quán lớn (res_001, res_002, res_003) đủ điều kiện
    valid_ids = [s.id for s in validated]
    assert valid_ids == ["res_001", "res_002", "res_003"]
    assert len(validated) == 3

    # 3 quán còn lại bị loại với lý do tương ứng
    dis_reasons = {d["store_id"]: d["reason"] for d in disqualified}
    assert dis_reasons["res_004"] == "khong_dat_nguong_luot_danh_gia"  # Quán 2 reviews
    assert dis_reasons["res_005"] == "diem_danh_gia_goc_thap"          # Quán 3.2★
    assert dis_reasons["res_006"] == "khong_dat_nguong_luot_danh_gia"  # Quán 15 reviews


def test_compute_weighted_percentile() -> None:
    values = [20000, 30000, 50000, 80000]
    weights = [1.0, 1.0, 1.0, 1.0]

    p50 = compute_weighted_percentile(values, weights, 50.0)
    assert p50 in (30000, 50000)

    # Nếu dồn trọng số lớn vào món 30000
    heavy_weights = [0.1, 10.0, 0.1, 0.1]
    p50_heavy = compute_weighted_percentile(values, heavy_weights, 50.0)
    assert p50_heavy == 30000


def test_compute_price_distribution_from_dishes() -> None:
    dishes_with_weights = [
        (DishItem(name="Cà phê đen", price=25000), 0.9),
        (DishItem(name="Cà phê sữa", price=32000), 0.9),
        (DishItem(name="Bạc xỉu", price=39000), 0.8),
        (DishItem(name="Trà đào", price=55000), 0.8),
        (DishItem(name="Trà matcha", price=59000), 0.7),
    ]

    dist = compute_price_distribution(dishes_with_weights)

    assert dist.sample_size == 5
    assert dist.min_price == 25000
    assert dist.max_price == 59000
    assert dist.median_price in (32000, 39000)
    assert dist.p25_price <= dist.median_price <= dist.p75_price
    assert dist.sweet_spot_range == [dist.p25_price, dist.p75_price]


def test_empty_dishes_returns_zero_distribution() -> None:
    dist = compute_price_distribution([])
    assert dist.sample_size == 0
    assert dist.median_price == 0
    assert dist.sweet_spot_range == [0, 0]
