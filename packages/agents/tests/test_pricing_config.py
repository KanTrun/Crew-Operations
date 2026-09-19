# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho loader tham số nghiệp vụ AG-PRICING (plan mục 1.5).

Plan mục 1.5: "Không tự chốt thay chủ dự án các tham số nghiệp vụ được đánh dấu
[ĐỀ XUẤT MỚI]" — chúng chỉ được phép tồn tại dưới dạng DEFAULT CÓ THỂ CẤU HÌNH
trong file config riêng, mỗi khóa gắn nhãn BUSINESS_DECISION_PENDING_REVIEW.

Test này chứng minh:
1. Loader fail-fast khi thiếu khóa/sai kiểu (không âm thầm rơi về default khác file).
2. File `config/khao-sat-gia-tham-so.yaml` thật parse được và khớp đúng các con số
   trong plan (mục 1.1, 1.3, 1.4, 1.5.1, 1.5.7, 4.1, 4.2, 4.3, 4.4, 4.5, 2.2).
3. MỌI khóa [ĐỀ XUẤT MỚI] đều có nhãn BUSINESS_DECISION_PENDING_REVIEW trong file.
4. Giá trị trong config khớp với default của hàm Math Layer — tức đổi số là đổi
   hành vi, không có "default ẩn" thứ hai nằm trong mã.

Không network, không LLM. Các test đọc đĩa chỉ đọc file config của repo.
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest
import yaml
from ca_agents.ag_pricing import math_layer
from ca_agents.ag_pricing.pricing_config import (
    CONFIG_PATH,
    ROOT,
    AmbiConfig,
    CostPlusConfig,
    DualGateConfig,
    PercentileConfig,
    PricingConfig,
    PricingConfigError,
    SweetSpotConfig,
    _reset_pricing_config_cache,
    get_pricing_config,
    load_pricing_config,
    parse_pricing_config,
)

NHAN_CHO_DUYET = "BUSINESS_DECISION_PENDING_REVIEW"


def _du_lieu_chuan() -> dict[str, Any]:
    """Fixture dict mô phỏng đúng cấu trúc file config — dùng cho test fail-fast."""
    return {
        "phien_ban": "1.0.0",
        "schema_version_hop_dong": "2.1",
        "phan_vi": {
            "method": "linear",
            "min_sample_size": 5,
            "gia_hop_le_toi_thieu_vnd": 5000,
            "gia_hop_le_toi_da_vnd": 2000000,
        },
        "dual_gate": {
            "min_review_count": 50,
            "min_rating": 4.2,
            "min_weighted_rating": 4.0,
            "bayes_m": 50,
            "bayes_prior_c": 4.2,
            "distance_decay_alpha": 0.15,
            "low_confidence_review_threshold": 10,
            "low_confidence_weight_factor": 0.5,
        },
        "radius_profile_mac_dinh": {"dine_in_km": 1.0, "delivery_km": 5.0},
        "ambi": {
            "trong_so_core": 0.5,
            "trong_so_substitutes": 0.5,
            "he_so_vung_rui_ro": 1.2,
        },
        "sweet_spot": {
            "phan_vi_canh_duoi": 40,
            "phan_vi_canh_tren": 60,
            "dung_gia_goc": True,
            "tach_theo_tang_dinh_vi": True,
            "loai_tru_combo": True,
        },
        "lam_tron_hien_thi": {"beverage": 1000, "mon_chinh": 5000, "mac_dinh": 5000},
        "cost_plus": {"target_margin_ratio_mac_dinh": 0.30},
        "canh_tranh": {"pi": 3.14159},
        "ocr_guardrail": {"nguong_lech_sigma": 2.0, "confidence_can_review": "low"},
    }


# ── 1. Parse hàm thuần ───────────────────────────────────────────────────────


def test_parse_fixture_chuan_tra_ve_dung_gia_tri() -> None:
    cfg = parse_pricing_config(_du_lieu_chuan())

    assert cfg.phien_ban == "1.0.0"
    assert cfg.schema_version_hop_dong == "2.1"
    assert cfg.phan_vi == PercentileConfig(
        method="linear", min_sample_size=5,
        gia_hop_le_toi_thieu_vnd=5000, gia_hop_le_toi_da_vnd=2000000,
    )
    assert cfg.dual_gate == DualGateConfig(
        min_review_count=50, min_rating=4.2, min_weighted_rating=4.0,
        bayes_m=50, bayes_prior_c=4.2, distance_decay_alpha=0.15,
        low_confidence_review_threshold=10, low_confidence_weight_factor=0.5,
    )
    assert cfg.radius_profile_mac_dinh == (1.0, 5.0)
    assert cfg.ambi == AmbiConfig(trong_so_core=0.5, trong_so_substitutes=0.5, he_so_vung_rui_ro=1.2)
    assert cfg.sweet_spot == SweetSpotConfig(
        phan_vi_canh_duoi=40.0, phan_vi_canh_tren=60.0,
        dung_gia_goc=True, tach_theo_tang_dinh_vi=True, loai_tru_combo=True,
    )
    assert cfg.lam_tron_hien_thi == (1000, 5000, 5000)
    assert cfg.cost_plus == CostPlusConfig(target_margin_ratio_mac_dinh=0.30)
    assert cfg.pi == pytest.approx(3.14159)
    assert cfg.ocr_nguong_lech_sigma == pytest.approx(2.0)
    assert cfg.ocr_confidence_can_review == "low"


def test_parse_la_ham_thuan_cung_input_cung_output() -> None:
    """ADR-002: parse không phụ thuộc trạng thái ẩn, không đọc đĩa, không network."""
    du_lieu = _du_lieu_chuan()
    assert parse_pricing_config(du_lieu) == parse_pricing_config(du_lieu)


def test_parse_khong_dot_chay_input() -> None:
    du_lieu = _du_lieu_chuan()
    snapshot = repr(du_lieu)
    parse_pricing_config(du_lieu)
    assert repr(du_lieu) == snapshot


# ── 2. Fail-fast khi config sai ───────────────────────────────────────────────


def test_config_goc_khong_phai_mapping() -> None:
    with pytest.raises(PricingConfigError, match="mapping ở gốc"):
        parse_pricing_config(["khong", "phai", "dict"])


@pytest.mark.parametrize(
    "section",
    [
        "phan_vi", "dual_gate", "radius_profile_mac_dinh", "ambi", "sweet_spot",
        "lam_tron_hien_thi", "cost_plus", "canh_tranh", "ocr_guardrail",
    ],
)
def test_thieu_section_bat_buoc_thi_bao_loi(section: str) -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu.pop(section)
    with pytest.raises(PricingConfigError, match=re.escape(section)):
        parse_pricing_config(du_lieu)


@pytest.mark.parametrize(
    ("section", "khoa"),
    [
        ("root", "phien_ban"),
        ("root", "schema_version_hop_dong"),
        ("phan_vi", "method"),
        ("phan_vi", "min_sample_size"),
        ("phan_vi", "gia_hop_le_toi_thieu_vnd"),
        ("phan_vi", "gia_hop_le_toi_da_vnd"),
        ("dual_gate", "min_review_count"),
        ("dual_gate", "min_rating"),
        ("dual_gate", "min_weighted_rating"),
        ("dual_gate", "bayes_m"),
        ("dual_gate", "bayes_prior_c"),
        ("dual_gate", "distance_decay_alpha"),
        ("dual_gate", "low_confidence_review_threshold"),
        ("dual_gate", "low_confidence_weight_factor"),
        ("radius_profile_mac_dinh", "dine_in_km"),
        ("radius_profile_mac_dinh", "delivery_km"),
        ("ambi", "trong_so_core"),
        ("ambi", "trong_so_substitutes"),
        ("ambi", "he_so_vung_rui_ro"),
        ("sweet_spot", "phan_vi_canh_duoi"),
        ("sweet_spot", "phan_vi_canh_tren"),
        ("sweet_spot", "dung_gia_goc"),
        ("sweet_spot", "tach_theo_tang_dinh_vi"),
        ("sweet_spot", "loai_tru_combo"),
        ("lam_tron_hien_thi", "beverage"),
        ("lam_tron_hien_thi", "mon_chinh"),
        ("lam_tron_hien_thi", "mac_dinh"),
        ("cost_plus", "target_margin_ratio_mac_dinh"),
        ("canh_tranh", "pi"),
        ("ocr_guardrail", "nguong_lech_sigma"),
        ("ocr_guardrail", "confidence_can_review"),
    ],
)
def test_thieu_khoa_bat_buoc_thi_bao_loi(section: str, khoa: str) -> None:
    """Không được âm thầm dùng default khi file config thiếu khóa (plan mục 1.5)."""
    du_lieu = _du_lieu_chuan()
    if section == "root":
        du_lieu.pop(khoa)
    else:
        du_lieu[section].pop(khoa)

    with pytest.raises(PricingConfigError, match=re.escape(khoa)):
        parse_pricing_config(du_lieu)


@pytest.mark.parametrize(
    ("section", "khoa", "gia_tri_sai"),
    [
        ("phan_vi", "method", 123),
        ("phan_vi", "min_sample_size", "nam"),
        ("dual_gate", "min_rating", "cao"),
        ("dual_gate", "bayes_m", None),
        ("sweet_spot", "dung_gia_goc", "true"),   # chuỗi, không phải bool YAML
        ("sweet_spot", "loai_tru_combo", 1),      # int, không phải bool
        ("lam_tron_hien_thi", "beverage", "nghin"),
        ("ocr_guardrail", "confidence_can_review", ""),
        ("ocr_guardrail", "confidence_can_review", None),
    ],
)
def test_sai_kieu_thi_bao_loi(section: str, khoa: str, gia_tri_sai: Any) -> None:
    du_lieu = _du_lieu_chuan()
    if section == "root":
        du_lieu[khoa] = gia_tri_sai
    else:
        du_lieu[section][khoa] = gia_tri_sai

    with pytest.raises(PricingConfigError, match=re.escape(khoa)):
        parse_pricing_config(du_lieu)


def test_chuoi_so_van_duoc_chap_nhan() -> None:
    """YAML hay bị quote số (`pi: "3.14"`) — loader chấp nhận vì giá trị không đổi.

    Chỉ chuỗi KHÔNG parse ra số mới là lỗi (xem `test_sai_kieu_thi_bao_loi`).
    """
    du_lieu = _du_lieu_chuan()
    du_lieu["canh_tranh"]["pi"] = "3.14"
    du_lieu["dual_gate"]["min_review_count"] = "50"
    cfg = parse_pricing_config(du_lieu)

    assert cfg.pi == pytest.approx(3.14)
    assert cfg.dual_gate.min_review_count == 50


def test_section_khong_phai_mapping_thi_bao_loi() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["ambi"] = "0.5"
    with pytest.raises(PricingConfigError, match="ambi"):
        parse_pricing_config(du_lieu)


def test_loi_bao_ro_file_nao_khoa_nao() -> None:
    """Thông báo lỗi phải chỉ đúng section + khóa để người vận hành tự sửa được."""
    du_lieu = _du_lieu_chuan()
    du_lieu["dual_gate"].pop("bayes_prior_c")
    with pytest.raises(PricingConfigError) as exc:
        parse_pricing_config(du_lieu)
    assert "dual_gate" in str(exc.value)
    assert "bayes_prior_c" in str(exc.value)


# ── 3. Đọc file config thật ───────────────────────────────────────────────────


def test_file_config_that_ton_tai_dung_duong_dan() -> None:
    assert CONFIG_PATH == ROOT / "config" / "khao-sat-gia-tham-so.yaml"
    assert CONFIG_PATH.exists(), f"thiếu file cấu hình: {CONFIG_PATH}"


def test_load_file_config_that_thanh_cong() -> None:
    cfg = load_pricing_config()
    assert isinstance(cfg, PricingConfig)
    assert cfg.phien_ban
    assert cfg.schema_version_hop_dong == "2.1"


def test_load_file_khong_ton_tai_thi_bao_loi(tmp_path: Path) -> None:
    with pytest.raises(PricingConfigError, match="không tìm thấy file cấu hình"):
        load_pricing_config(tmp_path / "khong-ton-tai.yaml")


def test_file_that_khop_cac_con_so_trong_plan() -> None:
    """Đối chiếu ngược: con số trong file phải đúng bằng con số plan đã ghi."""
    cfg = load_pricing_config()

    # Plan mục 1.4: Gate 1 v >= 50; Gate 2 R >= 4.2 và WR >= 4.0
    assert cfg.dual_gate.min_review_count == 50
    assert cfg.dual_gate.min_rating == pytest.approx(4.2)
    assert cfg.dual_gate.min_weighted_rating == pytest.approx(4.0)
    # Plan mục 1.3: AMBI = 0.5·Core + 0.5·mean(Subs)
    assert cfg.ambi.trong_so_core == pytest.approx(0.5)
    assert cfg.ambi.trong_so_substitutes == pytest.approx(0.5)
    # Plan mục 4.3: 42.000 × 1.2 = 50.400
    assert cfg.ambi.he_so_vung_rui_ro == pytest.approx(1.2)
    # Plan mục 4.4: P40 / min(AMBI, P60)
    assert cfg.sweet_spot.phan_vi_canh_duoi == pytest.approx(40.0)
    assert cfg.sweet_spot.phan_vi_canh_tren == pytest.approx(60.0)
    # Plan mục 1.5.7: đồ uống bội 1.000đ, món chính bội 5.000đ
    assert cfg.lam_tron_hien_thi == (1000, 5000, 5000)
    # Plan mục 4.5: diện tích = PI · r²
    assert cfg.pi == pytest.approx(3.14159)
    # Plan mục 1.1: dine-in 500m–1.5km, delivery 3–7km → mặc định nằm trong khoảng
    dine_in, delivery = cfg.radius_profile_mac_dinh
    assert 0.5 <= dine_in <= 1.5
    assert 3.0 <= delivery <= 7.0


def test_file_that_khong_co_khoa_thua_lam_hong_loader() -> None:
    """File có khóa bổ sung (ghi_chu, ngay_kiem, food_cost_chuan_nganh...) vẫn parse được."""
    cfg = load_pricing_config()
    assert cfg.cost_plus.target_margin_ratio_mac_dinh == pytest.approx(0.30)


# ── 4. Nhãn BUSINESS_DECISION_PENDING_REVIEW (plan mục 1.5) ───────────────────


def test_moi_tham_so_de_xuat_moi_deu_co_nhan_cho_duyet() -> None:
    """Plan mục 1.5: mỗi tham số [ĐỀ XUẤT MỚI] phải gắn nhãn trong file config.

    Danh sách đối chiếu lấy từ IMPLEMENTATION_STATUS.md / báo cáo Phase 1.
    """
    noi_dung = CONFIG_PATH.read_text(encoding="utf-8")
    cac_khoa_can_nhan = [
        "min_sample_size",              # plan mục 4.1
        "min_weighted_rating",          # plan mục 1.4
        "bayes_prior_c",                # plan mục 1.4
        "low_confidence_review_threshold",  # plan mục 4.2
        "low_confidence_weight_factor",     # KHÔNG có trong plan
        "dine_in_km",                   # plan mục 1.1 (radius_profile)
        "trong_so_core",                # plan mục 1.3
        "he_so_vung_rui_ro",            # plan mục 4.3
        "phan_vi_canh_duoi",            # plan mục 4.4
        "beverage",                     # plan mục 1.5.7
        "target_margin_ratio_mac_dinh", # plan mục 1.5.1
        "nguong_lech_sigma",            # plan mục 2.2
        "confidence_can_review",        # plan mục 2.2
    ]
    for khoa in cac_khoa_can_nhan:
        assert khoa in noi_dung, f"file config thiếu khóa '{khoa}'"
    assert noi_dung.count(NHAN_CHO_DUYET) >= len(cac_khoa_can_nhan)


def test_nhan_cho_duyet_chi_dung_muc_trong_plan() -> None:
    """Nhãn phải trỏ về đúng mục plan để chủ dự án duyệt nhanh.

    Chỉ xét dòng mà nhãn ĐỨNG ĐẦU phần comment — dòng giải thích ở header
    ("Mọi khóa gắn nhãn BUSINESS_DECISION_...") không phải là một nhãn.
    """
    noi_dung = CONFIG_PATH.read_text(encoding="utf-8")
    so_nhan = 0
    for dong in noi_dung.splitlines():
        if not dong.strip().startswith(f"# {NHAN_CHO_DUYET}"):
            continue
        so_nhan += 1
        assert re.search(r"plan mục \d", dong) or "KHÔNG có trong plan" in dong, (
            f"nhãn thiếu nguồn tham chiếu: {dong.strip()}"
        )
    assert so_nhan >= 10, f"chỉ thấy {so_nhan} nhãn — nghi ngờ file config bị mất nhãn"


def test_file_config_ghi_ro_khong_hard_code_trong_ma() -> None:
    noi_dung = CONFIG_PATH.read_text(encoding="utf-8")
    assert "KHÔNG hard-code" in noi_dung


# ── 5. Default trong mã phải khớp config (không có "default ẩn" thứ hai) ──────


def test_default_cua_ham_math_layer_khop_voi_config() -> None:
    """Nếu config và default trong mã lệch nhau, đổi config sẽ không đổi hành vi."""
    cfg = load_pricing_config()

    assert math_layer.percentile_linear.__defaults__ is None
    assert cfg.phan_vi.method == "linear"
    assert math_layer._PERCENTILE_METHOD == cfg.phan_vi.method

    # is_valid_price
    sig = _defaults_of(math_layer.is_valid_price)
    assert sig["min_vnd"] == cfg.phan_vi.gia_hop_le_toi_thieu_vnd
    assert sig["max_vnd"] == cfg.phan_vi.gia_hop_le_toi_da_vnd

    # compute_percentile_stats
    sig = _defaults_of(math_layer.compute_percentile_stats)
    assert sig["min_sample_size"] == cfg.phan_vi.min_sample_size

    # weighted_rating
    sig = _defaults_of(math_layer.weighted_rating)
    assert sig["m"] == cfg.dual_gate.bayes_m
    assert sig["prior_c"] == pytest.approx(cfg.dual_gate.bayes_prior_c)

    # passes_gates
    sig = _defaults_of(math_layer.passes_gates)
    assert sig["min_v"] == cfg.dual_gate.min_review_count
    assert sig["min_r"] == pytest.approx(cfg.dual_gate.min_rating)
    assert sig["min_wr"] == pytest.approx(cfg.dual_gate.min_weighted_rating)

    # is_low_confidence / sample_weight
    assert _defaults_of(math_layer.is_low_confidence)["review_threshold"] == (
        cfg.dual_gate.low_confidence_review_threshold
    )
    assert _defaults_of(math_layer.sample_weight)["low_confidence_factor"] == pytest.approx(
        cfg.dual_gate.low_confidence_weight_factor
    )

    # distance_decay_weight
    assert _defaults_of(math_layer.distance_decay_weight)["alpha"] == pytest.approx(
        cfg.dual_gate.distance_decay_alpha
    )

    # compute_ambi / risk_zone_threshold / price_zone
    sig = _defaults_of(math_layer.compute_ambi)
    assert sig["w_core"] == pytest.approx(cfg.ambi.trong_so_core)
    assert sig["w_subs"] == pytest.approx(cfg.ambi.trong_so_substitutes)
    assert _defaults_of(math_layer.risk_zone_threshold)["he_so"] == pytest.approx(
        cfg.ambi.he_so_vung_rui_ro
    )
    assert _defaults_of(math_layer.price_zone)["he_so"] == pytest.approx(
        cfg.ambi.he_so_vung_rui_ro
    )

    # compute_sweet_spot
    sig = _defaults_of(math_layer.compute_sweet_spot)
    assert sig["p_low"] == pytest.approx(cfg.sweet_spot.phan_vi_canh_duoi)
    assert sig["p_high"] == pytest.approx(cfg.sweet_spot.phan_vi_canh_tren)
    assert sig["rounding_steps"] == cfg.lam_tron_hien_thi

    # round_to_market_convention
    assert _defaults_of(math_layer.round_to_market_convention)["rounding_steps"] == (
        cfg.lam_tron_hien_thi
    )

    # min_viable_price
    assert _defaults_of(math_layer.min_viable_price)["target_margin_ratio"] == pytest.approx(
        cfg.cost_plus.target_margin_ratio_mac_dinh
    )

    # competitive_intensity
    assert _defaults_of(math_layer.competitive_intensity)["pi"] == pytest.approx(cfg.pi)


def _defaults_of(ham: Any) -> dict[str, Any]:
    """Đọc keyword-default của hàm để đối chiếu với config."""
    import inspect

    params = inspect.signature(ham).parameters
    return {
        ten: p.default
        for ten, p in params.items()
        if p.default is not inspect.Parameter.empty
    }


def test_config_du_day_de_dieu_khien_toan_bo_math_layer() -> None:
    """Chạy Math Layer bằng tham số LẤY TỪ CONFIG cho ra đúng số plan đã nêu."""
    cfg = load_pricing_config()

    # Plan mục 4.3: ví dụ AMBI 40.000 / 44.000 → 42.000; ngưỡng rủi ro 50.400
    ambi = math_layer.compute_ambi(
        40000.0, [44000.0],
        w_core=cfg.ambi.trong_so_core, w_subs=cfg.ambi.trong_so_substitutes,
    )
    assert ambi == pytest.approx(42000.0)
    nguong = math_layer.risk_zone_threshold(ambi, he_so=cfg.ambi.he_so_vung_rui_ro)
    assert nguong == pytest.approx(50400.0)
    assert math_layer.price_zone(60000.0, ambi, he_so=cfg.ambi.he_so_vung_rui_ro) == "rui_ro"

    # Plan mục 4.4.2: COGS 15.000, margin 0.3 → 21.428,57
    mvp = math_layer.min_viable_price(
        15000, target_margin_ratio=cfg.cost_plus.target_margin_ratio_mac_dinh
    )
    assert mvp == pytest.approx(15000 / 0.70)

    # Plan mục 4.5: 12 quán / bán kính 1km
    ci = math_layer.competitive_intensity(12, 1.0, pi=cfg.pi)
    assert ci == pytest.approx(12 / 3.14159)


# ── 6. Cache ──────────────────────────────────────────────────────────────────


def test_get_pricing_config_cache_cung_mot_instance() -> None:
    _reset_pricing_config_cache()
    try:
        lan_1 = get_pricing_config()
        lan_2 = get_pricing_config()
        assert lan_1 is lan_2
    finally:
        _reset_pricing_config_cache()


def test_reset_cache_lam_sach_trang_thai_an() -> None:
    _reset_pricing_config_cache()
    try:
        truoc = get_pricing_config()
        _reset_pricing_config_cache()
        sau = get_pricing_config()
        assert truoc is not sau
        assert truoc == sau
    finally:
        _reset_pricing_config_cache()


def test_dataclass_config_la_bat_bien() -> None:
    """Frozen dataclass → không ai sửa được tham số giữa chừng trong một lượt chạy."""
    cfg = load_pricing_config()
    with pytest.raises(FrozenInstanceError):
        cfg.pi = 3.0  # type: ignore[misc]


def test_file_yaml_that_la_yaml_hop_le() -> None:
    """Chống lỗi cú pháp YAML âm thầm (safe_load trả None)."""
    du_lieu = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(du_lieu, dict)
    assert du_lieu.get("phien_ban")
