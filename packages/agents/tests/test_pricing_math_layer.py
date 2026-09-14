"""Unit test cho Math Layer AG-PRICING (plan 260913-1455 mục 4.1–4.5).

Phase 1 Acceptance Criteria (plan mục 10): "100% unit test cho Math Layer pass".

ADR-002: các test này chạy OFFLINE — không network, không LLM, không DB,
không đọc đĩa (tham số truyền thẳng vào hàm). Cùng input → cùng output,
nên không cần seed và không có dao động giữa các lượt chạy.

Toàn bộ dữ liệu trong file này là DỮ LIỆU MÔ PHỎNG (simulated fixtures),
không phải số liệu thu thập thật từ ShopeeFood/Google Maps.
"""

from __future__ import annotations

import math

import pytest
from ca_agents.ag_pricing.math_layer import (
    SweetSpotZone,
    check_cost_plus_warning,
    collect_sweet_spot_prices,
    competitive_intensity,
    compute_ambi,
    compute_percentile_stats,
    compute_sweet_spot,
    distance_decay_weight,
    filter_valid_prices,
    is_low_confidence,
    is_valid_price,
    min_viable_price,
    passes_gates,
    percentile_linear,
    price_zone,
    risk_zone_threshold,
    round_to_market_convention,
    sample_weight,
    weighted_rating,
)
from ca_contracts.catchment_survey_v2 import (
    ChannelMode,
    MenuItemPrice,
    PercentileStats,
    PositioningTier,
    StoreRecord,
)

# Bội số làm tròn mặc định lấy từ config/khao-sat-gia-tham-so.yaml
# (beverage=1000, mon_chinh=5000, mac_dinh=5000). Truyền thẳng vào hàm để
# test không phụ thuộc việc đọc đĩa — ADR-002.
ROUNDING: tuple[int, int, int] = (1000, 5000, 5000)


def _store(**overrides: object) -> StoreRecord:
    """Quán mô phỏng (simulated) đạt chuẩn Dual-Gate."""
    base: dict[str, object] = {
        "store_id": "res_001",
        "name": "Cơm sườn 47",
        "lat": 10.762622,
        "lng": 106.660172,
        "review_count": 320,
        "rating": 4.6,
        "weighted_rating": 4.55,
        "passed_gate1": True,
        "passed_gate2": True,
    }
    base.update(overrides)
    return StoreRecord(**base)  # type: ignore[arg-type]


def _item(**overrides: object) -> MenuItemPrice:
    base: dict[str, object] = {
        "item_name_raw": "Cơm sườn bì chả",
        "item_name_normalized": "com_suon_bi_cha",
        "original_price_vnd": 45000,
        "effective_price_vnd": 45000,
        "source_channel": ChannelMode.DINE_IN_VISION,
        "confidence": "high",
    }
    base.update(overrides)
    return MenuItemPrice(**base)  # type: ignore[arg-type]


# ── 4.1 Phân vị & thống kê giá ───────────────────────────────────────────────


def test_percentile_linear_dung_noi_suy_tuyen_tinh_chuan() -> None:
    """Plan mục 4.1: method="linear" — kiểm bằng giá trị nội suy tính tay."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0]

    assert percentile_linear(values, 50.0) == pytest.approx(30.0)
    assert percentile_linear(values, 25.0) == pytest.approx(20.0)
    assert percentile_linear(values, 75.0) == pytest.approx(40.0)
    assert percentile_linear(values, 0.0) == pytest.approx(10.0)
    assert percentile_linear(values, 100.0) == pytest.approx(50.0)
    # Nội suy tuyến tính: P40 của [10..50] = 10 + 0.4*(50-10) = 26
    assert percentile_linear(values, 40.0) == pytest.approx(26.0)


def test_percentile_linear_noi_suy_giua_hai_mau() -> None:
    """Khác biệt cốt lõi so với percentile theo chỉ số (WIP substitute_matrix)."""
    # [1, 2, 3, 4]: P25 linear = 1.75, còn index-based int(4*0.25)=1 → 2.0
    assert percentile_linear([1.0, 2.0, 3.0, 4.0], 25.0) == pytest.approx(1.75)


def test_percentile_linear_khong_phu_thuoc_thu_tu_input() -> None:
    """Tất định: xáo thứ tự vẫn ra cùng kết quả (numpy tự sort)."""
    a = [45000.0, 30000.0, 52000.0, 38000.0, 41000.0]
    b = sorted(a)
    for q in (25.0, 40.0, 50.0, 60.0, 75.0):
        assert percentile_linear(a, q) == pytest.approx(percentile_linear(b, q))


def test_percentile_linear_rong_tra_ve_khong() -> None:
    """Rỗng → 0.0, không suy đoán. Caller phải kiểm `insufficient_data`."""
    assert percentile_linear([], 50.0) == 0.0


def test_percentile_linear_mot_mau() -> None:
    assert percentile_linear([42000.0], 25.0) == pytest.approx(42000.0)
    assert percentile_linear([42000.0], 75.0) == pytest.approx(42000.0)


def test_compute_percentile_stats_du_mau() -> None:
    values = [30000.0, 35000.0, 40000.0, 45000.0, 50000.0]

    stats = compute_percentile_stats(values, min_sample_size=5)

    assert isinstance(stats, PercentileStats)
    assert stats.insufficient_data is False
    assert stats.sample_size == 5
    assert stats.p25 == pytest.approx(35000.0)
    assert stats.p50 == pytest.approx(40000.0)
    assert stats.p75 == pytest.approx(45000.0)
    assert stats.p25 <= stats.p50 <= stats.p75


def test_compute_percentile_stats_duoi_nguong_mau_khong_tra_phan_vi() -> None:
    """Plan mục 4.1: n < 5 → KHÔNG tính phân vị, trả cờ insufficient_data=True.

    Đây là nền cho mã lỗi 422 INSUFFICIENT_MARKET_DATA (plan mục 5.3): thà báo
    "không đủ dữ liệu" còn hơn hiển thị một con số không đáng tin cho chủ quán.
    """
    for n in (0, 1, 2, 3, 4):
        stats = compute_percentile_stats([40000.0] * n, min_sample_size=5)
        assert stats.insufficient_data is True, f"n={n} phải bị gắn cờ"
        assert stats.sample_size == n
        assert (stats.p25, stats.p50, stats.p75) == (0.0, 0.0, 0.0)


def test_compute_percentile_stats_dung_nguong_mau_thi_tinh() -> None:
    stats = compute_percentile_stats([1.0, 2.0, 3.0, 4.0, 5.0], min_sample_size=5)
    assert stats.insufficient_data is False
    assert stats.sample_size == 5


def test_compute_percentile_stats_nguong_tuy_chinh() -> None:
    stats = compute_percentile_stats([1.0, 2.0, 3.0], min_sample_size=3)
    assert stats.insufficient_data is False
    assert stats.p50 == pytest.approx(2.0)


def test_is_valid_price_loc_gia_ngoai_khoang_va_nan() -> None:
    assert is_valid_price(45000.0) is True
    assert is_valid_price(5000.0) is True
    assert is_valid_price(2_000_000.0) is True

    # Nhiễu OCR/parse: giá 0, giá 10đ, giá 99 tỷ
    assert is_valid_price(0.0) is False
    assert is_valid_price(10.0) is False
    assert is_valid_price(99_000_000_000.0) is False
    assert is_valid_price(-1.0) is False

    # NaN/inf phải bị loại — nếu không sẽ làm hỏng toàn bộ phân vị
    assert is_valid_price(float("nan")) is False
    assert is_valid_price(float("inf")) is False
    assert is_valid_price(float("-inf")) is False


def test_is_valid_price_tuy_chinh_khoang() -> None:
    assert is_valid_price(900.0, min_vnd=500, max_vnd=1000) is True
    assert is_valid_price(1500.0, min_vnd=500, max_vnd=1000) is False


def test_filter_valid_prices_bao_toan_thu_tu() -> None:
    raw = [45000.0, 0.0, 38000.0, float("nan"), 99_000_000_000.0, 52000.0]
    assert filter_valid_prices(raw) == [45000.0, 38000.0, 52000.0]


def test_filter_valid_prices_rong() -> None:
    assert filter_valid_prices([]) == []


# ── 4.2 Dual-Gate Qualification ──────────────────────────────────────────────


def test_weighted_rating_keo_quan_it_review_ve_prior() -> None:
    """Plan mục 1.4: WR ngăn quán 2 review 5.0★ leo lên top."""
    wr_small = weighted_rating(2, 5.0, m=50, prior_c=4.2)
    # (2/52)*5.0 + (50/52)*4.2 = 0.1923 + 4.0385 = 4.2308
    assert wr_small == pytest.approx(4.230769, abs=1e-5)
    assert wr_small < 4.3

    wr_large = weighted_rating(2000, 4.8, m=50, prior_c=4.2)
    # (2000/2050)*4.8 + (50/2050)*4.2 = 4.6829 + 0.1024 = 4.7854
    assert wr_large == pytest.approx(4.785366, abs=1e-5)
    assert wr_large > wr_small


def test_weighted_rating_khong_review_thi_bang_prior() -> None:
    """v=0 → WR = C. Không có dữ liệu thì về prior, không bịa."""
    assert weighted_rating(0, 5.0, m=50, prior_c=4.2) == pytest.approx(4.2)
    assert weighted_rating(0, 0.0, m=50, prior_c=4.2) == pytest.approx(4.2)


def test_weighted_rating_review_am_bi_kep_ve_khong() -> None:
    """Dữ liệu lỗi (review_count âm) không được làm nổ công thức."""
    assert weighted_rating(-100, 5.0, m=50, prior_c=4.2) == pytest.approx(4.2)


def test_weighted_rating_m_bang_khong_thi_giu_nguyen_rating() -> None:
    assert weighted_rating(320, 4.6, m=0, prior_c=4.2) == pytest.approx(4.6)


def test_passes_gates_dung_chu_cong_thuc_plan_muc_4_2() -> None:
    store = _store(review_count=320, rating=4.6, weighted_rating=4.55)
    assert passes_gates(store, min_v=50, min_r=4.2, min_wr=4.0) == (True, True)


def test_passes_gates_gate1_dung_badge_thay_the_so_review() -> None:
    """Plan mục 1.4: Gate 1 = v >= 50 HOẶC có nhãn "Quán yêu thích"."""
    badge = _store(review_count=3, rating=4.6, weighted_rating=4.55, has_favorite_badge=True)
    no_badge = _store(review_count=3, rating=4.6, weighted_rating=4.55, has_favorite_badge=False)

    assert passes_gates(badge, min_v=50, min_r=4.2, min_wr=4.0) == (True, True)
    assert passes_gates(no_badge, min_v=50, min_r=4.2, min_wr=4.0) == (False, True)


def test_passes_gates_gate2_can_ca_rating_va_wr() -> None:
    """Plan mục 1.4: Gate 2 = R >= 4.2 VÀ WR >= 4.0 — thiếu một là rớt."""
    rating_thap = _store(review_count=320, rating=4.1, weighted_rating=4.5)
    wr_thap = _store(review_count=320, rating=4.6, weighted_rating=3.9)
    ca_hai_thap = _store(review_count=320, rating=4.1, weighted_rating=3.9)

    assert passes_gates(rating_thap, min_v=50, min_r=4.2, min_wr=4.0) == (True, False)
    assert passes_gates(wr_thap, min_v=50, min_r=4.2, min_wr=4.0) == (True, False)
    assert passes_gates(ca_hai_thap, min_v=50, min_r=4.2, min_wr=4.0) == (True, False)


def test_passes_gates_ranh_gioi_dung_bang_nguong_van_dat() -> None:
    """Bất đẳng thức trong plan là >=, không phải >."""
    store = _store(review_count=50, rating=4.2, weighted_rating=4.0)
    assert passes_gates(store, min_v=50, min_r=4.2, min_wr=4.0) == (True, True)


def test_passes_gates_tra_rieng_hai_co_de_ui_dien_giai() -> None:
    """Plan mục 6.2: UI phải nói được vì sao rớt → không gộp thành một bool."""
    store = _store(review_count=3, rating=3.5, weighted_rating=3.4)
    gate1, gate2 = passes_gates(store, min_v=50, min_r=4.2, min_wr=4.0)
    assert gate1 is False
    assert gate2 is False


def test_is_low_confidence_chi_gan_khi_nho_badge_ma_it_review() -> None:
    """Plan mục 4.2: badge + review_count < 10 → low_confidence."""
    assert is_low_confidence(_store(review_count=3, has_favorite_badge=True), review_threshold=10) is True
    assert is_low_confidence(_store(review_count=9, has_favorite_badge=True), review_threshold=10) is True
    # Đủ review → không phải low confidence dù có badge
    assert is_low_confidence(_store(review_count=10, has_favorite_badge=True), review_threshold=10) is False
    assert is_low_confidence(_store(review_count=320, has_favorite_badge=True), review_threshold=10) is False
    # Không badge → không phải low confidence theo định nghĩa này
    assert is_low_confidence(_store(review_count=3, has_favorite_badge=False), review_threshold=10) is False


def test_low_confidence_la_co_khong_phai_ly_do_loai_bo() -> None:
    """Plan mục 4.2: quán low_confidence "vẫn được tính nhưng với trọng số giảm"."""
    store = _store(
        review_count=3,
        rating=4.6,
        weighted_rating=4.55,
        has_favorite_badge=True,
        low_confidence=True,
    )
    gate1, gate2 = passes_gates(store, min_v=50, min_r=4.2, min_wr=4.0)
    assert (gate1, gate2) == (True, True)
    assert store.passes_dual_gate is True
    # Vẫn có trọng số > 0
    assert sample_weight(store, low_confidence_factor=0.5) == pytest.approx(0.5)


def test_sample_weight_giam_theo_he_so_low_confidence() -> None:
    normal = _store(low_confidence=False)
    flagged = _store(review_count=3, has_favorite_badge=True, low_confidence=True)

    assert sample_weight(normal, low_confidence_factor=0.5) == pytest.approx(1.0)
    assert sample_weight(flagged, low_confidence_factor=0.5) == pytest.approx(0.5)
    assert sample_weight(flagged, low_confidence_factor=0.25) == pytest.approx(0.25)


def test_sample_weight_khong_dat_gate_thi_bang_khong() -> None:
    """Quán rớt gate không được đóng góp vào phân vị giá."""
    assert sample_weight(_store(passed_gate1=False), low_confidence_factor=0.5) == 0.0
    assert sample_weight(_store(passed_gate2=False), low_confidence_factor=0.5) == 0.0
    assert (
        sample_weight(_store(passed_gate1=False, passed_gate2=False), low_confidence_factor=0.5)
        == 0.0
    )


def test_distance_decay_weight_giam_dan_theo_khoang_cach() -> None:
    """Plan mục 1.1: W = 1/(1 + alpha·d)."""
    w0 = distance_decay_weight(0.0, alpha=0.15)
    w1 = distance_decay_weight(1.0, alpha=0.15)
    w5 = distance_decay_weight(5.0, alpha=0.15)

    assert w0 == pytest.approx(1.0)
    assert w1 == pytest.approx(1.0 / 1.15)
    assert w5 == pytest.approx(1.0 / 1.75)
    assert w0 > w1 > w5 > 0.0


def test_distance_decay_weight_kep_khoang_cach_am() -> None:
    """Dữ liệu lỗi (d < 0) không được cho ra trọng số > 1."""
    assert distance_decay_weight(-5.0, alpha=0.15) == pytest.approx(1.0)


# ── 4.3 AMBI ─────────────────────────────────────────────────────────────────


def test_compute_ambi_dung_vi_du_trong_plan_muc_4_3() -> None:
    """Plan mục 4.3: Core median 40.000, mean substitute medians 44.000 → 42.000."""
    # (42.000 + 46.000) / 2 = 44.000
    ambi = compute_ambi(40000.0, [42000.0, 46000.0], w_core=0.5, w_subs=0.5)
    assert ambi == pytest.approx(42000.0)


def test_compute_ambi_mot_nhom_thay_the() -> None:
    assert compute_ambi(40000.0, [48000.0], w_core=0.5, w_subs=0.5) == pytest.approx(44000.0)


def test_compute_ambi_khong_co_nhom_thay_the_thi_bang_median_core() -> None:
    """Không chia 0, không bịa: chỉ có món lõi thì AMBI = Median(Core)."""
    assert compute_ambi(40000.0, [], w_core=0.5, w_subs=0.5) == pytest.approx(40000.0)


def test_compute_ambi_trong_so_tuy_chinh() -> None:
    """Trọng số là tham số config (BUSINESS_DECISION_PENDING_REVIEW, plan mục 1.3)."""
    assert compute_ambi(40000.0, [50000.0], w_core=0.7, w_subs=0.3) == pytest.approx(43000.0)
    assert compute_ambi(40000.0, [50000.0], w_core=0.3, w_subs=0.7) == pytest.approx(47000.0)


def test_risk_zone_threshold_dung_vi_du_plan() -> None:
    """Plan mục 4.3: 42.000 × 1.2 = 50.400."""
    assert risk_zone_threshold(42000.0, he_so=1.2) == pytest.approx(50400.0)
    assert risk_zone_threshold(0.0, he_so=1.2) == 0.0


def test_price_zone_phan_dung_ba_vung_theo_plan_muc_1_3() -> None:
    ambi = 42000.0
    # <= AMBI → an toàn
    assert price_zone(40000.0, ambi, he_so=1.2) == "an_toan"
    assert price_zone(42000.0, ambi, he_so=1.2) == "an_toan"
    # > AMBI*1.2 → rủi ro
    assert price_zone(50401.0, ambi, he_so=1.2) == "rui_ro"
    assert price_zone(70000.0, ambi, he_so=1.2) == "rui_ro"
    # khoảng giữa → cảnh báo
    assert price_zone(45000.0, ambi, he_so=1.2) == "canh_bao"
    assert price_zone(50400.0, ambi, he_so=1.2) == "canh_bao"


# ── 4.4 Sweet Spot ───────────────────────────────────────────────────────────

# Rổ giá Core ∪ Substitutes cùng tier (dữ liệu mô phỏng), đã loại combo.
RO_GIA: list[float] = [
    30000.0, 32000.0, 35000.0, 38000.0, 40000.0,
    42000.0, 45000.0, 48000.0, 50000.0, 55000.0,
]


def test_compute_sweet_spot_dung_cong_thuc_plan_muc_4_4() -> None:
    """low_raw = P40(rổ); high_raw = min(AMBI, P60(rổ))."""
    p40 = percentile_linear(RO_GIA, 40.0)
    p60 = percentile_linear(RO_GIA, 60.0)

    zone = compute_sweet_spot(RO_GIA, ambi=99999.0, p_low=40.0, p_high=60.0,
                              category_group="mon_chinh", rounding_steps=ROUNDING)

    assert zone.low_raw == pytest.approx(p40)
    # AMBI cao hơn P60 → high_raw = P60
    assert zone.high_raw == pytest.approx(p60)
    assert zone.inverted is False
    assert zone.low_raw <= zone.high_raw


def test_compute_sweet_spot_ambi_chan_canh_tren() -> None:
    """Plan mục 4.4: high_raw = min(AMBI, P60) — AMBI thấp thì AMBI thắng."""
    p60 = percentile_linear(RO_GIA, 60.0)
    assert p60 > 40000.0

    zone = compute_sweet_spot(RO_GIA, ambi=40000.0, p_low=40.0, p_high=60.0,
                              category_group="mon_chinh", rounding_steps=ROUNDING)

    assert zone.high_raw == pytest.approx(40000.0)
    assert zone.inverted is False


def test_compute_sweet_spot_lam_tron_chi_o_tang_hien_thi() -> None:
    """Plan mục 1.5.7: `_raw` giữ nguyên, `_display` mới làm tròn."""
    zone = compute_sweet_spot(RO_GIA, ambi=99999.0, p_low=40.0, p_high=60.0,
                              category_group="mon_chinh", rounding_steps=ROUNDING)

    # P40 của RO_GIA = 39200 → làm tròn bội 5000 = 40000; kiểm bằng bất biến
    assert zone.low_display % 5000 == 0
    assert zone.high_display % 5000 == 0
    assert abs(zone.low_display - zone.low_raw) <= 5000 / 2
    assert abs(zone.high_display - zone.high_raw) <= 5000 / 2
    # _raw KHÔNG bị ghi đè bởi giá làm tròn
    assert zone.low_raw == pytest.approx(percentile_linear(RO_GIA, 40.0))


def test_compute_sweet_spot_beverage_lam_tron_boi_1000() -> None:
    zone = compute_sweet_spot(RO_GIA, ambi=99999.0, p_low=40.0, p_high=60.0,
                              category_group="beverage", rounding_steps=ROUNDING)
    assert zone.low_display % 1000 == 0
    assert zone.high_display % 1000 == 0


def test_compute_sweet_spot_nhom_la_dung_boi_so_mac_dinh() -> None:
    zone = compute_sweet_spot(RO_GIA, ambi=99999.0, p_low=40.0, p_high=60.0,
                              category_group="nhom_chua_biet", rounding_steps=(1000, 5000, 5000))
    assert zone.low_display % 5000 == 0


def test_compute_sweet_spot_ambi_thap_hon_p40_danh_dao_khoang_lon() -> None:
    """GIẢ ĐỊNH NGOÀI PLAN: AMBI < P40 → khoảng giá bị lộn.

    Hàm GIỮ NGUYÊN kết quả công thức plan (high_raw = min(AMBI, P60)) và chỉ gắn
    cờ `inverted=True` để caller hiển thị cảnh báo. KHÔNG tự kẹp high_raw lên
    low_raw — kẹp sẽ phá bất biến "high_raw <= AMBI" của plan mục 4.4. Cách xử
    lý nghiệp vụ của ca này cần chủ dự án duyệt.
    """
    p40 = percentile_linear(RO_GIA, 40.0)
    zone = compute_sweet_spot(RO_GIA, ambi=1000.0, p_low=40.0, p_high=60.0,
                              category_group="mon_chinh", rounding_steps=ROUNDING)

    assert zone.inverted is True
    assert zone.high_raw == pytest.approx(1000.0)
    assert zone.low_raw == pytest.approx(p40)
    assert zone.high_raw < zone.low_raw
    # Bất biến "high_raw <= AMBI" vẫn đúng kể cả khi khoảng bị lộn
    assert zone.high_raw <= 1000.0


def test_compute_sweet_spot_rong_tra_ve_khoang_khong() -> None:
    zone = compute_sweet_spot([], ambi=0.0, p_low=40.0, p_high=60.0,
                              category_group="mon_chinh", rounding_steps=ROUNDING)
    assert zone == SweetSpotZone(
        low_raw=0.0, high_raw=0.0, low_display=0, high_display=0, inverted=False
    )


def test_compute_sweet_spot_chan_p_low_lon_hon_p_high() -> None:
    with pytest.raises(ValueError, match="p_low"):
        compute_sweet_spot(RO_GIA, ambi=40000.0, p_low=60.0, p_high=40.0)


def test_round_to_market_convention_dung_chu_ham_plan_muc_4_4_1() -> None:
    """Plan mục 4.4.1: beverage → 1.000đ, còn lại → 5.000đ."""
    assert round_to_market_convention(42300.0, "beverage", ROUNDING) == 42000
    assert round_to_market_convention(42700.0, "beverage", ROUNDING) == 43000
    assert round_to_market_convention(42300.0, "mon_chinh", ROUNDING) == 40000
    assert round_to_market_convention(42700.0, "mon_chinh", ROUNDING) == 45000
    assert round_to_market_convention(0.0, "mon_chinh", ROUNDING) == 0


def test_round_to_market_convention_chan_boi_so_khong_duong() -> None:
    with pytest.raises(ValueError, match="bội số"):
        round_to_market_convention(42000.0, "mon_chinh", (1000, 0, 5000))


def test_collect_sweet_spot_prices_dung_gia_goc_khong_dung_gia_khuyen_mai() -> None:
    """Plan mục 1.5.2: Sweet Spot dùng giá niêm yết, không dùng giá khuyến mãi."""
    items = [
        _item(original_price_vnd=45000, effective_price_vnd=39000, is_promotional=True),
        _item(original_price_vnd=50000, effective_price_vnd=50000),
    ]
    assert collect_sweet_spot_prices(items, use_original_price=True) == [45000.0, 50000.0]
    assert collect_sweet_spot_prices(items, use_original_price=False) == [39000.0, 50000.0]


def test_collect_sweet_spot_prices_loai_combo_khoi_phan_vi_mon_le() -> None:
    """Plan mục 1.5.9: combo là phép tính gộp, không phải giá một món lẻ."""
    items = [
        _item(original_price_vnd=45000, effective_price_vnd=45000, is_combo=False),
        _item(item_name_raw="Combo 2 người", original_price_vnd=120000,
              effective_price_vnd=120000, is_combo=True),
    ]
    assert collect_sweet_spot_prices(items, exclude_combo=True) == [45000.0]
    assert collect_sweet_spot_prices(items, exclude_combo=False) == [45000.0, 120000.0]


def test_collect_sweet_spot_prices_rong() -> None:
    assert collect_sweet_spot_prices([]) == []


def test_collect_sweet_spot_prices_bo_qua_mon_khong_doc_duoc_gia() -> None:
    """Contract cho phép `original_price_vnd=None` (ảnh mờ, OCR không đọc được giá).

    Trước đây hàm gọi thẳng `float(None)` → TypeError làm SẬP CẢ JOB khảo sát chỉ vì
    một món trong một ảnh mờ. Món không có giá phải bị LOẠI khỏi rổ, không thay bằng
    0 (sẽ kéo phân vị xuống giả tạo) và không suy ngược từ giá khuyến mãi (plan 1.5.2:
    khuyến mãi không phải mặt bằng giá thị trường).
    """
    items = [
        _item(original_price_vnd=45000, effective_price_vnd=45000),
        _item(item_name_raw="Món mờ", original_price_vnd=None, effective_price_vnd=0),
        _item(original_price_vnd=50000, effective_price_vnd=50000),
    ]
    assert collect_sweet_spot_prices(items, use_original_price=True) == [45000.0, 50000.0]


def test_collect_sweet_spot_prices_gia_khuyen_mai_khong_bao_gio_none() -> None:
    """`effective_price_vnd` là int bắt buộc nên nhánh use_original_price=False không None.

    Giữ test này để nếu sau này contract nới `effective_price_vnd` thành Optional thì
    nhánh còn lại cũng phải được xử lý None — không chỉ nhánh giá gốc.
    """
    items = [_item(original_price_vnd=None, effective_price_vnd=39000)]
    assert collect_sweet_spot_prices(items, use_original_price=False) == [39000.0]


# ── 4.4.2 Cost-Plus Sanity Check ─────────────────────────────────────────────


def test_min_viable_price_dung_cong_thuc_plan_muc_4_4_2() -> None:
    """MinViablePrice = COGS / (1 − margin)."""
    # 15.000 / 0.7 = 21.428,57
    assert min_viable_price(15000, target_margin_ratio=0.30) == pytest.approx(21428.5714, abs=1e-3)
    assert min_viable_price(0, target_margin_ratio=0.30) == pytest.approx(0.0)
    assert min_viable_price(20000, target_margin_ratio=0.50) == pytest.approx(40000.0)


def test_min_viable_price_chan_margin_ngoai_khoang() -> None:
    for bad in (0.0, 1.0, 1.5, -0.1):
        with pytest.raises(ValueError, match="target_margin_ratio"):
            min_viable_price(15000, target_margin_ratio=bad)


def test_min_viable_price_chan_cogs_am() -> None:
    with pytest.raises(ValueError, match="estimated_cogs_vnd"):
        min_viable_price(-1000, target_margin_ratio=0.30)


def test_check_cost_plus_warning_canh_bao_khi_tran_thap_hon_gia_hoa_von() -> None:
    """Plan mục 1.5.1: Sweet Spot cao < MinViablePrice → cảnh báo lỗ biên."""
    assert check_cost_plus_warning(40000.0, 45000.0) is True
    assert check_cost_plus_warning(45000.0, 45000.0) is False
    assert check_cost_plus_warning(50000.0, 45000.0) is False


def test_check_cost_plus_warning_khong_khai_cogs_thi_khong_canh_bao() -> None:
    """Chủ quán không khai COGS → không có cơ sở cảnh báo, không bịa."""
    assert check_cost_plus_warning(40000.0, None) is False


def test_cost_plus_la_canh_bao_khong_phai_lenh_chan() -> None:
    """ADR-008: hệ thống nêu vấn đề, chủ quán quyết. Không có cờ "chặn"."""
    min_viable = min_viable_price(35000, target_margin_ratio=0.30)  # 50.000
    zone = compute_sweet_spot(RO_GIA, ambi=99999.0, p_low=40.0, p_high=60.0,
                              category_group="mon_chinh", rounding_steps=ROUNDING)

    warning = check_cost_plus_warning(zone.high_raw, min_viable)
    # Kết quả vẫn là một khoảng giá hợp lệ — chỉ kèm cờ cảnh báo
    assert isinstance(warning, bool)
    assert zone.low_raw <= zone.high_raw
    assert zone.inverted is False


# ── 4.5 Competitive Intensity ────────────────────────────────────────────────


def test_competitive_intensity_dung_cong_thuc_plan_muc_4_5() -> None:
    """CI = số quán đạt chuẩn / (PI · r²), PI = 3.14159 theo plan."""
    # 12 quán / (3.14159 * 1) = 3.8197
    assert competitive_intensity(12, 1.0, pi=3.14159) == pytest.approx(12 / 3.14159)
    # 30 quán / (3.14159 * 25) = 0.38197
    assert competitive_intensity(30, 5.0, pi=3.14159) == pytest.approx(30 / (3.14159 * 25))


def test_competitive_intensity_ban_kinh_khong_duong_tra_ve_khong() -> None:
    """Chia 0 phải được chặn — trả 0.0 thay vì inf/nan."""
    assert competitive_intensity(12, 0.0, pi=3.14159) == 0.0
    assert competitive_intensity(12, -1.0, pi=3.14159) == 0.0


def test_competitive_intensity_khong_co_quan_dat_chuan() -> None:
    assert competitive_intensity(0, 3.0, pi=3.14159) == 0.0


def test_competitive_intensity_so_quan_am_bi_kep_ve_khong() -> None:
    assert competitive_intensity(-5, 3.0, pi=3.14159) == 0.0


def test_competitive_intensity_khong_dua_vao_cong_thuc_gia() -> None:
    """Plan mục 1.5.6: CI chỉ là NGỮ CẢNH. Hàm không nhận AMBI/Sweet Spot làm input."""
    import inspect

    from ca_agents.ag_pricing import math_layer

    params = set(inspect.signature(math_layer.competitive_intensity).parameters)
    assert params == {"qualified_store_count", "radius_km", "pi"}
    assert "ambi" not in params
    assert "sweet_spot" not in params


# ── ADR-002: Math Layer phải thuần ──────────────────────────────────────────


def test_math_layer_khong_import_llm_hay_network() -> None:
    """Plan mục 7 (architecture compliance): Math Layer không được import LLM/network.

    Kiểm bằng AST trên chính source file — không cần import-linter.
    """
    import ast
    from pathlib import Path

    src = Path(math_layer_path())
    tree = ast.parse(src.read_text(encoding="utf-8"))

    cam = {
        "httpx", "requests", "aiohttp", "urllib.request", "socket",
        "openai", "anthropic", "google.generativeai", "genai",
        "camoufox", "playwright", "sqlalchemy", "psycopg", "redis",
        "random", "time", "datetime",
    }
    vi_pham: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in cam or alias.name.split(".")[0] in {c.split(".")[0] for c in cam}:
                    vi_pham.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module in cam or node.module.split(".")[0] in {c.split(".")[0] for c in cam}:
                vi_pham.append(node.module)

    assert vi_pham == [], f"Math Layer import module cấm: {vi_pham}"


def math_layer_path() -> str:
    from pathlib import Path

    from ca_agents.ag_pricing import math_layer

    return str(Path(math_layer.__file__).resolve())


def test_math_layer_tat_dinh_giua_hai_lan_chay() -> None:
    """ADR-002: cùng input → cùng output, kể cả khi gọi lại nhiều lần."""
    for _ in range(3):
        assert percentile_linear(RO_GIA, 50.0) == pytest.approx(41000.0)
        assert compute_ambi(40000.0, [42000.0, 46000.0]) == pytest.approx(42000.0)
        assert competitive_intensity(12, 1.0) == pytest.approx(12 / 3.14159)
        assert round_to_market_convention(42300.0, "mon_chinh", ROUNDING) == 40000


def test_math_layer_khong_tra_ve_nan_hoac_inf() -> None:
    """Mọi đường biên phải trả số hữu hạn — NaN lọt vào UI là lỗi nghiêm trọng."""
    ket_qua = [
        percentile_linear([], 50.0),
        percentile_linear([0.0], 75.0),
        compute_ambi(0.0, []),
        compute_ambi(0.0, [0.0, 0.0]),
        risk_zone_threshold(0.0),
        competitive_intensity(0, 0.0),
        competitive_intensity(0, -3.0),
        distance_decay_weight(0.0),
        distance_decay_weight(-10.0),
        weighted_rating(0, 0.0),
        min_viable_price(0, 0.30),
        float(round_to_market_convention(0.0, "mon_chinh", ROUNDING)),
    ]
    for value in ket_qua:
        assert math.isfinite(value), f"giá trị không hữu hạn: {value}"


def test_percentile_stats_tu_math_layer_hop_le_voi_contract() -> None:
    """Kết quả Math Layer phải nhét vừa contract v2.1 (ADR-003)."""
    stats = compute_percentile_stats(RO_GIA, min_sample_size=5)
    assert stats.model_dump()["sample_size"] == len(RO_GIA)
    assert stats.p25 <= stats.p50 <= stats.p75

    thin = compute_percentile_stats([1.0, 2.0], min_sample_size=5)
    assert thin.model_dump()["insufficient_data"] is True


def test_positioning_tier_khong_dung_trong_math_layer() -> None:
    """Plan mục 1.5.3: lọc theo tier là việc của tầng tổng hợp, không phải Math Layer.

    Math Layer nhận rổ giá ĐÃ lọc cùng tier — kiểm bằng chữ ký hàm.
    """
    import inspect

    from ca_agents.ag_pricing import math_layer

    params = set(inspect.signature(math_layer.compute_sweet_spot).parameters)
    assert "positioning_tier" not in params
    # PositioningTier vẫn là một phần của contract, chỉ không phải input toán học
    assert PositioningTier.CASUAL_DINE_IN.value == "casual_dine_in"
