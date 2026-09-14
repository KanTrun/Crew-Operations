"""Math Layer — AG-PRICING (plan mục 4, v2.1).

ADR-002: MỌI con số nghiệp vụ (phân vị, WR, AMBI, Sweet Spot, MinViablePrice,
CompetitiveIntensity) nằm trong các hàm THUẦN ở module này.

CẤM trong module này:
- gọi LLM / model AI
- gọi network (httpx, camoufox, requests...)
- đọc/ghi DB
- đọc file (tham số đến từ `pricing_config`, đã load ở tầng ngoài)
- dùng `random`, `time.time()`, hoặc bất kỳ nguồn bất định nào

Cùng input → cùng output, offline hoàn toàn.

Phương pháp phân vị (plan mục 4.1): nội suy tuyến tính chuẩn, tương đương
`numpy.percentile(..., method="linear")`. Ghi rõ ở đây để mọi engineer dùng
MỘT phương pháp, tránh lệch số liệu giữa các lần chạy.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from ca_contracts.catchment_survey_v2 import (
    MenuItemPrice,
    PercentileStats,
    StoreRecord,
)

# numpy.percentile method — plan mục 4.1 yêu cầu nêu rõ trong docstring/module.
# Kiểu Literal (không phải str) để khớp overload đã type-hint của numpy.
_PERCENTILE_METHOD: Literal["linear"] = "linear"


# ── 4.1 Phân vị & thống kê giá ───────────────────────────────────────────────


def percentile_linear(values: Sequence[float], q: float) -> float:
    """Phân vị q (0–100) bằng nội suy tuyến tính chuẩn.

    Plan mục 4.1: dùng `numpy.percentile(..., method="linear")`.
    Rỗng → 0.0 (không suy đoán; caller phải kiểm `insufficient_data`).
    """
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=float), q, method=_PERCENTILE_METHOD))


def is_valid_price(price_vnd: float, *, min_vnd: int = 5000, max_vnd: int = 2_000_000) -> bool:
    """Lọc giá hợp lệ — chống nhiễu OCR/parse sai (plan mục 2.2, 4.1).

    NaN/inf bị loại. Khoảng [min_vnd, max_vnd] lấy từ config `phan_vi`.
    """
    if not np.isfinite(price_vnd):
        return False
    return min_vnd <= price_vnd <= max_vnd


def compute_percentile_stats(
    values: Sequence[float],
    *,
    min_sample_size: int = 5,
) -> PercentileStats:
    """P25/P50/P75 + cỡ mẫu.

    Plan mục 4.1: n < `min_sample_size` → KHÔNG tính phân vị, trả `sample_size`
    và cờ `insufficient_data=True`. Đây là cơ sở để ca_api trả 422
    INSUFFICIENT_MARKET_DATA (plan mục 5.3) thay vì hiển thị số không đáng tin.
    """
    n = len(values)
    if n < min_sample_size:
        return PercentileStats(sample_size=n, insufficient_data=True)

    return PercentileStats(
        p25=percentile_linear(values, 25.0),
        p50=percentile_linear(values, 50.0),
        p75=percentile_linear(values, 75.0),
        sample_size=n,
        insufficient_data=False,
    )


def filter_valid_prices(
    values: Iterable[float],
    *,
    min_vnd: int = 5000,
    max_vnd: int = 2_000_000,
) -> list[float]:
    """Giữ lại các giá nằm trong khoảng hợp lệ, bảo toàn thứ tự input."""
    return [v for v in values if is_valid_price(v, min_vnd=min_vnd, max_vnd=max_vnd)]


# ── 4.2 Dual-Gate Qualification ──────────────────────────────────────────────


def weighted_rating(
    review_count: int,
    rating: float,
    *,
    m: int = 50,
    prior_c: float = 4.2,
) -> float:
    """Điểm Bayesian: WR = (v/(v+m))·R + (m/(v+m))·C.

    Plan mục 1.4 / 4.2. `m` = số review tối thiểu để tin, `prior_c` = điểm
    trung bình thị trường. v=0 → WR = C (không có dữ liệu thì về prior).
    """
    v = max(0, int(review_count))
    denom = v + m
    if denom <= 0:
        return float(prior_c)
    return (v / denom) * float(rating) + (m / denom) * float(prior_c)


def passes_gates(
    store: StoreRecord,
    *,
    min_v: int = 50,
    min_r: float = 4.2,
    min_wr: float = 4.0,
) -> tuple[bool, bool]:
    """Dual-Gate theo plan mục 4.2 — giữ nguyên chữ công thức trong plan.

    - Gate 1 (Volume): `review_count >= min_v` HOẶC có nhãn "Quán yêu thích".
    - Gate 2 (Quality): `rating >= min_r` VÀ `weighted_rating >= min_wr`.

    Trả `(gate1, gate2)` để caller lưu riêng từng cờ vào StoreRecord — không
    gộp thành một bool, vì UI cần diễn giải lý do rớt (plan mục 6.2).
    """
    gate1 = store.review_count >= min_v or store.has_favorite_badge
    gate2 = store.rating >= min_r and store.weighted_rating >= min_wr
    return gate1, gate2


def is_low_confidence(
    store: StoreRecord,
    *,
    review_threshold: int = 10,
) -> bool:
    """Plan mục 4.2: qua Gate 1 NHỜ BADGE nhưng `review_count < ngưỡng`.

    Đây là CỜ cảnh báo, KHÔNG phải lý do loại bỏ — quán vẫn được tính nhưng
    với trọng số giảm (xem `sample_weight`).
    """
    return store.has_favorite_badge and store.review_count < review_threshold


def sample_weight(
    store: StoreRecord,
    *,
    low_confidence_factor: float = 0.5,
) -> float:
    """Trọng số mẫu khi tổng hợp phân vị.

    Plan mục 4.2: quán `low_confidence` "vẫn được tính nhưng với trọng số giảm".
    Plan KHÔNG cho con số cụ thể → `low_confidence_factor` là tham số config
    (BUSINESS_DECISION_PENDING_REVIEW), mặc định 0.5.

    Quán không đạt cả hai gate → trọng số 0 (không đóng góp vào phân vị).
    """
    if not (store.passed_gate1 and store.passed_gate2):
        return 0.0
    if store.low_confidence:
        return float(low_confidence_factor)
    return 1.0


# ── 4.3 AMBI ─────────────────────────────────────────────────────────────────


def compute_ambi(
    core_median: float,
    substitute_medians: Sequence[float],
    *,
    w_core: float = 0.5,
    w_subs: float = 0.5,
) -> float:
    """AMBI = w_core·Median(Core) + w_subs·mean(Median các nhóm thay thế).

    Plan mục 1.3 / 4.3. Trọng số 0.5/0.5 giữ nguyên từ v1.0
    (BUSINESS_DECISION_PENDING_REVIEW — plan mục 1.3).

    Không có nhóm thay thế nào → AMBI = Median(Core) (không chia 0, không bịa).
    """
    if not substitute_medians:
        return float(core_median)
    mean_subs = float(np.mean(np.asarray(substitute_medians, dtype=float)))
    return float(w_core) * float(core_median) + float(w_subs) * mean_subs


def risk_zone_threshold(ambi: float, *, he_so: float = 1.2) -> float:
    """Ngưỡng vùng rủi ro = AMBI × hệ số (plan mục 1.3 / 4.3: 42.000 × 1.2 = 50.400)."""
    return float(ambi) * float(he_so)


def price_zone(price_vnd: float, ambi: float, *, he_so: float = 1.2) -> str:
    """Phân vùng giá so với AMBI (plan mục 1.3).

    - `price <= AMBI`            → "an_toan"
    - `price >  AMBI × he_so`    → "rui_ro"
    - khoảng giữa                → "canh_bao"

    Trả reason code tiếng Việt snake_case theo convention repo.
    """
    if price_vnd <= ambi:
        return "an_toan"
    if price_vnd > risk_zone_threshold(ambi, he_so=he_so):
        return "rui_ro"
    return "canh_bao"


# ── 4.4 Sweet Spot Pricing Zone ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SweetSpotZone:
    """Kết quả Sweet Spot — tách `_raw` (lưu trữ) và `_display` (hiển thị).

    Plan mục 1.5.7: KHÔNG ghi đè `_raw` bằng giá đã làm tròn, vì tầng phân tích
    sau cần số chính xác. `inverted=True` khi AMBI < P_low (xem `compute_sweet_spot`).
    """

    low_raw: float
    high_raw: float
    low_display: int
    high_display: int
    inverted: bool = False


def compute_sweet_spot(
    prices: Sequence[float],
    ambi: float,
    *,
    p_low: float = 40.0,
    p_high: float = 60.0,
    category_group: str = "mon_chinh",
    rounding_steps: tuple[int, int, int] = (1000, 5000, 5000),
) -> SweetSpotZone:
    """Sweet Spot theo plan mục 4.4 — [ĐỀ XUẤT MỚI], chờ chủ dự án duyệt công thức.

        SweetSpot_low_raw  = P{p_low}(Core ∪ Substitutes | cùng tier)
        SweetSpot_high_raw = min(AMBI, P{p_high}(Core ∪ Substitutes | cùng tier))

    `prices` phải là rổ ĐÃ GỘP Core ∪ Substitutes, ĐÃ lọc cùng
    `positioning_tier` (plan mục 1.5.3) và ĐÃ loại combo (plan mục 1.5.9).

    GIẢ ĐỊNH NGOÀI PLAN: khi AMBI < P{p_low} (mặt bằng giá nhóm thay thế rẻ hơn
    hẳn món lõi) thì công thức plan cho ra `high_raw < low_raw` — khoảng giá bị
    lộn. Hàm này GIỮ NGUYÊN kết quả công thức (không tự kẹp, vì kẹp sẽ phá bất
    biến `high_raw = min(AMBI, P60)`) và chỉ đặt `inverted=True` để caller hiển
    thị cảnh báo thay vì vẽ một khoảng vô nghĩa. Cách xử lý nghiệp vụ của ca này
    cần chủ dự án duyệt.
    """
    if p_low > p_high:
        raise ValueError(f"p_low ({p_low}) phải <= p_high ({p_high})")

    low_raw = percentile_linear(prices, p_low)
    high_raw = min(float(ambi), percentile_linear(prices, p_high))

    return SweetSpotZone(
        low_raw=low_raw,
        high_raw=high_raw,
        low_display=round_to_market_convention(low_raw, category_group, rounding_steps),
        high_display=round_to_market_convention(high_raw, category_group, rounding_steps),
        inverted=high_raw < low_raw,
    )


def collect_sweet_spot_prices(
    items: Iterable[MenuItemPrice],
    *,
    exclude_combo: bool = True,
    use_original_price: bool = True,
) -> list[float]:
    """Rút rổ giá dùng cho Sweet Spot từ danh sách món.

    Plan mục 1.5.2: Sweet Spot dùng `original_price_vnd` (giá niêm yết), KHÔNG
    dùng giá khuyến mãi — vì khuyến mãi là chiến thuật ngắn hạn, không phải mặt
    bằng giá thị trường.
    Plan mục 1.5.9: loại combo khỏi phân vị món lẻ.

    Món KHÔNG đọc được giá thì bị LOẠI khỏi rổ, không thay bằng 0 và không suy
    ngược từ giá khuyến mãi: contract cho phép `original_price_vnd=None` (ảnh mờ),
    và một dòng giá 0đ sẽ kéo phân vị xuống giả tạo — tệ hơn là thiếu một mẫu.
    """
    out: list[float] = []
    for item in items:
        if exclude_combo and item.is_combo:
            continue
        price: int | None = (
            item.original_price_vnd if use_original_price else item.effective_price_vnd
        )
        if price is None:
            continue
        out.append(float(price))
    return out


def round_to_market_convention(
    price: float,
    category_group: str,
    rounding_steps: tuple[int, int, int] = (1000, 5000, 5000),
) -> int:
    """Làm tròn theo tâm lý giá thị trường VN (plan mục 1.5.7 / 4.4.1).

    `rounding_steps` = (beverage, mon_chinh, mac_dinh) lấy từ config
    `lam_tron_hien_thi` (BUSINESS_DECISION_PENDING_REVIEW — plan mục 1.5.7).

    CHỈ dùng ở tầng hiển thị. Không ghi đè giá trị `_raw`.
    """
    beverage_step, main_step, default_step = rounding_steps
    if category_group == "beverage":
        step = beverage_step
    elif category_group == "mon_chinh":
        step = main_step
    else:
        step = default_step
    if step <= 0:
        raise ValueError(f"bội số làm tròn phải > 0, nhận {step}")
    return int(round(float(price) / step) * step)


# ── 4.4.2 Cost-Plus Sanity Check ─────────────────────────────────────────────


def min_viable_price(
    estimated_cogs_vnd: int,
    target_margin_ratio: float = 0.30,
) -> float:
    """MinViablePrice = COGS / (1 − margin) — plan mục 1.5.1 / 4.4.2.

    `target_margin_ratio` mặc định 0.30 là ĐỀ XUẤT (BUSINESS_DECISION_PENDING_REVIEW
    — plan mục 1.5.1). Chủ quán có thể override qua `CostPlusCheck`.
    """
    if not 0.0 < target_margin_ratio < 1.0:
        raise ValueError(f"target_margin_ratio phải trong (0, 1), nhận {target_margin_ratio}")
    if estimated_cogs_vnd < 0:
        raise ValueError(f"estimated_cogs_vnd phải >= 0, nhận {estimated_cogs_vnd}")
    return float(estimated_cogs_vnd) / (1.0 - float(target_margin_ratio))


def check_cost_plus_warning(
    sweet_spot_high_raw: float,
    min_viable: float | None,
) -> bool:
    """True khi trần vùng Sweet Spot thấp hơn giá hoà vốn mục tiêu.

    Plan mục 1.5.1: đây là CẢNH BÁO cho chủ quán, không phải lệnh chặn.
    ADR-008: hệ thống không tự đổi giá — chỉ nêu vấn đề để người quyết.
    `min_viable=None` (chủ quán không khai COGS) → không cảnh báo.
    """
    if min_viable is None:
        return False
    return float(sweet_spot_high_raw) < float(min_viable)


# ── 4.5 Competitive Intensity ────────────────────────────────────────────────


def competitive_intensity(
    qualified_store_count: int,
    radius_km: float,
    *,
    pi: float = 3.14159,
) -> float:
    """Mật độ quán đạt chuẩn / km² — plan mục 4.5.

    Chỉ là NGỮ CẢNH diễn giải (AreaContext). Plan mục 1.5.6 nêu rõ: KHÔNG đưa
    chỉ số này vào AMBI hay Sweet Spot — tránh biến nó thành công thức giá trá hình.

    GIẢ ĐỊNH NGOÀI PLAN: plan viết `area_km2 = pi * radius_km**2` nên bán kính âm
    vẫn cho diện tích dương và một con số CI "trông hợp lệ". Hàm này kẹp
    `radius_km` về >= 0 (giống `distance_decay_weight`) để bán kính vô nghĩa trả
    về 0.0 thay vì âm thầm bịa mật độ cạnh tranh.

    GIẢ ĐỊNH NGOÀI PLAN (2): bán kính cực nhỏ (cỡ subnormal) cho `area_km2` dương
    nhưng nhỏ tới mức `count / area` tràn thành `inf` — không serialize JSON được.
    Diện tích không phải số dương hữu hạn usable → trả 0.0, và kết quả luôn bị
    kẹp về hữu hạn. Bất biến: CI không âm, không NaN, không inf.
    """
    radius = max(0.0, float(radius_km))
    area_km2 = float(pi) * (radius ** 2)
    if not np.isfinite(area_km2) or area_km2 <= 0:
        return 0.0
    ci = max(0, int(qualified_store_count)) / area_km2
    return ci if np.isfinite(ci) else 0.0


# ── 1.1 Distance decay (dùng cho trọng số mẫu theo khoảng cách) ──────────────


def distance_decay_weight(distance_km: float, *, alpha: float = 0.15) -> float:
    """W = 1 / (1 + alpha·d) — plan mục 1.1, giữ nguyên từ WIP `qualifier.py`.

    d < 0 bị kẹp về 0 (khoảng cách âm là dữ liệu lỗi, không phải lý do đổi công thức).
    """
    d = max(0.0, float(distance_km))
    return 1.0 / (1.0 + float(alpha) * d)
