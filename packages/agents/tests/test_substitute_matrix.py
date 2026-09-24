# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Kiểm thử cho ma trận món thay thế liên ngành (Substitute Matrix) và chỉ số AMBI."""

from __future__ import annotations

from ca_agents.ag_pricing.substitute_matrix import (
    calculate_substitute_stats,
    classify_dish_category,
    compute_area_meal_budget_index,
    get_substitute_categories,
)
from ca_contracts.catchment_survey import DishItem, PriceDistribution


def test_get_substitute_categories_lunch_and_beverage() -> None:
    # Nhóm Cơm trưa
    com_subs = get_substitute_categories("cơm tấm")
    assert "bún" in com_subs
    assert "phở" in com_subs
    assert "hủ tiếu" in com_subs

    # Nhóm Cà phê
    cafe_subs = get_substitute_categories("cà phê muối")
    assert "trà trái cây" in cafe_subs
    assert "trà sữa" in cafe_subs


def test_classify_dish_category() -> None:
    assert classify_dish_category("Cơm tấm sườn bì chả", "cơm") == "core"
    assert classify_dish_category("Bún bò Huế đặc biệt", "cơm") == "bún"
    assert classify_dish_category("Phở tái lăn", "cơm") == "phở"
    assert classify_dish_category("Hủ tiếu Nam Vang", "cơm") == "hủ tiếu"
    assert classify_dish_category("Trà đá", "cơm") == "do_uong_kem"


def test_calculate_substitute_stats() -> None:
    dishes = [
        DishItem(name="Bún bò Huế", price=35000),
        DishItem(name="Bún mọc", price=38000),
        DishItem(name="Bún chả", price=42000),
    ]
    stats = calculate_substitute_stats("bún", dishes)
    assert stats is not None
    assert stats.category_name == "bún"
    assert stats.dishes_count == 3
    assert stats.median_price == 38000
    assert stats.min_price == 35000
    assert stats.max_price == 42000


def test_compute_area_meal_budget_index() -> None:
    core_dist = PriceDistribution(
        sample_size=10,
        min_price=30000,
        max_price=50000,
        median_price=40000,
        p25_price=35000,
        p75_price=45000,
        volume_weighted_mean=41000,
        sweet_spot_range=[35000, 45000],
    )

    sub_dishes_bun = [DishItem(name="Bún bò", price=36000)]
    sub_dishes_pho = [DishItem(name="Phở bò", price=38000)]

    stat_bun = calculate_substitute_stats("bún", sub_dishes_bun)
    stat_pho = calculate_substitute_stats("phở", sub_dishes_pho)
    assert stat_bun and stat_pho

    # Core median = 40.000đ, Sub avg median = 37.000đ
    # AMBI = 50% * 40k + 50% * 37k = 38.500đ -> làm tròn 39.000đ hoặc 38.000đ
    ambi = compute_area_meal_budget_index(core_dist, [stat_bun, stat_pho])
    assert 38000 <= ambi <= 39000
