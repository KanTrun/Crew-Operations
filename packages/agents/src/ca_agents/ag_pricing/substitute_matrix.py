"""Ma trận sản phẩm thay thế (Substitute Matrix) & Nhu cầu cốt lõi F&B (Jobs-to-be-Done).

Trong F&B, khách hàng không ra quyết định theo từ khóa hẹp mà theo nhu cầu (Share of Stomach):
- Nhu cầu ăn trưa/no bụng (Quick Lunch): Cơm <-> Bún <-> Phở <-> Hủ tiếu <-> Bánh mì.
- Nhu cầu thức uống/trò chuyện (Beverage & Third Place): Cà phê <-> Trà trái cây <-> Trà sữa <-> Nước ép.
"""

from __future__ import annotations

from ca_contracts.catchment_survey import (
    DishItem,
    PriceDistribution,
    SubstituteCategoryStats,
)

# Bản đồ ánh xạ nhu cầu F&B theo nhóm (Jobs-to-be-Done)
_MEAL_GROUPS: dict[str, list[str]] = {
    "cơm": ["bún", "phở", "hủ tiếu", "bánh mì", "bánh canh"],
    "bún": ["cơm", "phở", "hủ tiếu", "bánh canh", "bánh mì"],
    "phở": ["cơm", "bún", "hủ tiếu", "miến", "bánh mì"],
    "hủ tiếu": ["cơm", "bún", "phở", "bánh canh", "mì"],
    "bánh mì": ["cơm", "bún", "xôi", "hủ tiếu"],
    "cà phê": ["trà trái cây", "trà sữa", "nước ép", "sinh tố"],
    "trà sữa": ["trà trái cây", "cà phê", "chè", "nước ép"],
    "trà trái cây": ["trà sữa", "cà phê", "nước ép", "sinh tố"],
    "lẩu": ["nướng", "quán nhậu", "món việt"],
    "nướng": ["lẩu", "quán nhậu", "bia tuyết"],
    "ăn vặt": ["bánh tráng", "chè", "kem", "gà rán", "trà sữa"],
}


def get_substitute_categories(keyword: str) -> list[str]:
    """Tìm danh sách các nhóm món thay thế trực tiếp dựa trên từ khóa cốt lõi."""
    kw = (keyword or "").strip().lower()
    if not kw:
        return []

    # Tìm nhóm khớp chính xác hoặc khớp từ khóa
    for group_key, subs in _MEAL_GROUPS.items():
        if group_key in kw or kw in group_key:
            return list(subs)

    # Nếu từ khóa chứa các món cơm cụ thể
    if any(k in kw for k in ("com", "cơm", "tam", "tấm", "sườn")):
        return ["bún", "phở", "hủ tiếu", "bánh mì", "bánh canh"]

    # Nếu từ khóa chứa nước uống / cà phê
    if any(k in kw for k in ("cafe", "cà phê", "coffee", "muối", "bạc xỉu")):
        return ["trà trái cây", "trà sữa", "nước ép", "sinh tố"]

    return []


def classify_dish_category(dish_name: str, core_keyword: str) -> str:
    """Phân loại món ăn vào nhóm 'core' hoặc nhóm thay thế cụ thể."""
    name = dish_name.strip().lower()
    core = core_keyword.strip().lower()

    if core in name:
        return "core"

    # Nhận diện các nhóm thay thế phổ biến
    for cat in ["cơm", "bún", "phở", "hủ tiếu", "bánh mì", "bánh canh", "mì", "trà sữa", "trà trái cây", "cà phê", "nước ép"]:
        if cat in name:
            return cat

    # Đồ uống phụ trợ kèm món ăn
    if any(d in name for d in ("trà đá", "nước ngọt", "pepsi", "coca", "sting", "khăn lạnh")):
        return "do_uong_kem"

    return "mon_khac"


def calculate_substitute_stats(
    category_name: str,
    dishes: list[DishItem],
) -> SubstituteCategoryStats | None:
    """Tính toán thống kê phân vị cho một danh mục món thay thế."""
    valid_dishes = [d for d in dishes if 10000 <= d.price <= 500000]
    if not valid_dishes:
        return None

    prices = sorted([d.price for d in valid_dishes])
    n = len(prices)

    min_p = prices[0]
    max_p = prices[-1]
    p25 = prices[int(n * 0.25)]
    median_p = prices[int(n * 0.5)]
    p75 = prices[min(n - 1, int(n * 0.75))]

    return SubstituteCategoryStats(
        category_name=category_name,
        dishes_count=n,
        median_price=median_p,
        min_price=min_p,
        max_price=max_p,
        p25_price=p25,
        p75_price=p75,
        sweet_spot_range=[p25, p75],
    )


def compute_area_meal_budget_index(
    core_dist: PriceDistribution,
    substitute_stats: list[SubstituteCategoryStats],
) -> int:
    """Tính chỉ số Trần ngân sách bữa ăn của khu vực (Area Meal Budget Index - AMBI).

    Trọng số: 50% từ Median món chính + 50% từ trung bình Median các món thay thế.
    """
    if core_dist.sample_size == 0 and not substitute_stats:
        return 0

    core_median = core_dist.median_price
    if not substitute_stats:
        return core_median

    sub_medians = [s.median_price for s in substitute_stats if s.dishes_count > 0]
    if not sub_medians:
        return core_median

    avg_sub_median = sum(sub_medians) / len(sub_medians)

    if core_dist.sample_size == 0:
        ambi = avg_sub_median
    else:
        ambi = (core_median * 0.5) + (avg_sub_median * 0.5)

    # Làm tròn đến 1.000 VNĐ
    return int(round(ambi / 1000.0) * 1000)
