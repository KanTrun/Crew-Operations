"""Unit test cho Contracts & Math Layer AG-PREDICT (plan 260918 mục 3, 4).

Phase 1 Acceptance Criteria (plan mục 10): "100% unit test cho contracts + math
layer pass".

ADR-002: các test này chạy OFFLINE — không network, không LLM, không DB.
Cùng input → cùng output.

Toàn bộ dữ liệu trong file này là DỮ LIỆU MÔ PHỎNG (simulated fixtures).
"""

from __future__ import annotations

import math

from ca_agents.ag_predict.math_layer import (
    detect_success_patterns,
    doanh_thu_moi,
    loi_nhuan_them_nhan_su,
    phan_ra_mua,
    price_elasticity,
)
from ca_contracts.ops_predict import (
    PositiveRule,
    PositiveRuleStatus,
    PredictResponse,
    SuccessPattern,
    SuccessPatternSource,
    SuccessPatternType,
    TwinScenario,
    TwinScenarioType,
)

# ── Contracts validation ─────────────────────────────────────────────────────


def test_success_pattern_valid() -> None:
    p = SuccessPattern(
        pattern_id="pat_1",
        loai=SuccessPatternType.CA_DOANH_THU,
        mo_ta="Ca tối T6 doanh thu cao",
        do_tin_cay=0.9,
        bang_chung=["ca_1"],
        nguon=SuccessPatternSource.LICH_SU_DOANH_THU,
    )
    assert p.do_tin_cay == 0.9
    assert p.loai == "ca_doanh_thu"


def test_success_pattern_clamps_do_tin_cay() -> None:
    p = SuccessPattern(
        pattern_id="pat_1",
        loai=SuccessPatternType.MON_BAN_CHAY,
        mo_ta="Món bán chạy",
        do_tin_cay=1.5,  # vượt 1.0 → clamp
        nguon=SuccessPatternSource.LICH_SU_BAN,
    )
    assert p.do_tin_cay == 1.0


def test_positive_rule_default_status() -> None:
    r = PositiveRule(
        id="rule_1",
        cau="Tăng cường 1 nhân viên ca tối T6",
        do_tin_cay=0.8,
    )
    assert r.trang_thai == PositiveRuleStatus.DE_XUAT


def test_twin_scenario_valid() -> None:
    s = TwinScenario(
        scenario_id="sc_1",
        loai=TwinScenarioType.TANG_GIA,
        tham_so={"mon_id": "caphe_sua_da", "gia_moi": 30000},
        baseline={"doanh_thu": 1000000},
        ket_qua={"doanh_thu": 1100000},
        rui_ro="Có thể mất khách",
    )
    assert s.loai == "tang_gia"


def test_predict_response_defaults() -> None:
    resp = PredictResponse()
    assert resp.suggestions == []
    assert resp.patterns == []
    assert resp.twin_scenarios == []


# ── Math Layer: phát hiện mẫu thành công ─────────────────────────────────────


def test_detect_success_patterns_ca_doanh_thu() -> None:
    doanh_thu_by_ca = {
        "T2_sang": 100.0,
        "T2_chieu": 110.0,
        "T2_toi": 105.0,
        "T6_toi": 500.0,  # outlier dương
        "T7_toi": 480.0,  # outlier dương
    }
    patterns = detect_success_patterns(
        doanh_thu_by_ca=doanh_thu_by_ca,
        doanh_thu_by_mon={},
        ton_kho_by_time={},
    )
    ca_patterns = [p for p in patterns if p.loai == SuccessPatternType.CA_DOANH_THU]
    assert len(ca_patterns) >= 1
    assert all(p.do_tin_cay > 0 for p in ca_patterns)


def test_detect_success_patterns_insufficient_data() -> None:
    # Ít hơn min_sample (3) → không phát hiện
    patterns = detect_success_patterns(
        doanh_thu_by_ca={"T2": 100.0, "T3": 110.0},
        doanh_thu_by_mon={},
        ton_kho_by_time={},
    )
    assert patterns == []


def test_detect_success_patterns_mon_ban_chay() -> None:
    patterns = detect_success_patterns(
        doanh_thu_by_ca={},
        doanh_thu_by_mon={
            "caphe_sua_da": 100.0,
            "tra_dao": 110.0,
            "caphe_den": 105.0,
            "matcha": 500.0,  # bán chạy
            "socola": 480.0,
        },
        ton_kho_by_time={},
    )
    mon_patterns = [p for p in patterns if p.loai == SuccessPatternType.MON_BAN_CHAY]
    assert len(mon_patterns) >= 1


# ── Math Layer: độ co giãn giá ───────────────────────────────────────────────


def test_price_elasticity_tang_gia_giam_luong() -> None:
    # Tăng giá 20%, hệ số -0.5 → lượng giảm 10%
    luong_moi = price_elasticity(gia_cu=25000, gia_moi=30000, luong_ban_cu=100)
    assert math.isclose(luong_moi, 90.0, rel_tol=1e-6)


def test_price_elasticity_giam_gia_tang_luong() -> None:
    # Giảm giá 20%, hệ số -0.5 → lượng tăng 10%
    luong_moi = price_elasticity(gia_cu=30000, gia_moi=24000, luong_ban_cu=100)
    assert math.isclose(luong_moi, 110.0, rel_tol=1e-6)


def test_price_elasticity_gia_cu_zero() -> None:
    assert price_elasticity(gia_cu=0, gia_moi=100, luong_ban_cu=50) == 50.0


# ── Math Layer: doanh thu mới ────────────────────────────────────────────────


def test_doanh_thu_moi() -> None:
    # 30000 × 90 − 50000 = 2650000
    assert math.isclose(doanh_thu_moi(30000, 90, 50000), 2650000.0)


# ── Math Layer: lợi nhuận thêm nhân sự ───────────────────────────────────────


def test_loi_nhuan_them_nhan_su() -> None:
    # 200000 − 150000 = 50000
    assert math.isclose(loi_nhuan_them_nhan_su(200000, 150000), 50000.0)


# ── Math Layer: phân rã mùa ──────────────────────────────────────────────────


def test_phan_ra_mua() -> None:
    doanh_thu_by_ngay = {
        "T2": 100.0,
        "T3": 100.0,
        "T4": 100.0,
        "T5": 100.0,
        "T6": 200.0,  # gấp đôi trung bình
        "T7": 200.0,
        "CN": 100.0,
    }
    he_so = phan_ra_mua(doanh_thu_by_ngay)
    avg = sum(doanh_thu_by_ngay.values()) / 7  # 128.57
    assert math.isclose(he_so["T6"], 200.0 / avg, rel_tol=1e-6)
    assert math.isclose(he_so["T2"], 100.0 / avg, rel_tol=1e-6)


def test_phan_ra_mua_empty() -> None:
    he_so = phan_ra_mua({})
    assert all(v == 0.0 for v in he_so.values())