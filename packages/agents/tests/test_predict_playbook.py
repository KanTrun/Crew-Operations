"""Unit test cho AG-PREDICT playbook tích cực (plan 260918 mục 2.2, Phase 2).

ADR-008: luật tích cực chỉ là đề xuất (de_xuat), không tự áp dụng.
"""

from __future__ import annotations

from ca_agents.ag_predict.playbook_positive import de_xuat_luat_tich_cuc
from ca_contracts.ops_predict import (
    PositiveRuleStatus,
    SuccessPattern,
    SuccessPatternSource,
    SuccessPatternType,
)


def _pattern(loai: SuccessPatternType, do_tin_cay: float, bang_chung: list[str]) -> SuccessPattern:
    return SuccessPattern(
        pattern_id="pat_1",
        loai=loai,
        mo_ta="Mẫu thành công",
        do_tin_cay=do_tin_cay,
        bang_chung=bang_chung,
        nguon=SuccessPatternSource.LICH_SU_DOANH_THU,
    )


def test_de_xuat_luat_tich_cuc_ca_doanh_thu() -> None:
    patterns = [
        _pattern(SuccessPatternType.CA_DOANH_THU, 0.9, ["T6_toi"]),
    ]
    rules = de_xuat_luat_tich_cuc(patterns)
    assert len(rules) == 1
    assert rules[0].trang_thai == PositiveRuleStatus.DE_XUAT
    assert "T6_toi" in rules[0].cau
    assert rules[0].dieu_kien == {"ca": "T6_toi"}


def test_de_xuat_luat_tich_cuc_mon_ban_chay() -> None:
    patterns = [
        _pattern(SuccessPatternType.MON_BAN_CHAY, 0.85, ["matcha"]),
    ]
    rules = de_xuat_luat_tich_cuc(patterns)
    assert len(rules) == 1
    assert rules[0].dieu_kien == {"mon": "matcha"}


def test_de_xuat_luat_tich_cuc_loai_do_tin_cay_thap() -> None:
    # do_tin_cay < 0.5 → không đề xuất (fail-closed)
    patterns = [
        _pattern(SuccessPatternType.CA_DOANH_THU, 0.3, ["T2_sang"]),
    ]
    rules = de_xuat_luat_tich_cuc(patterns)
    assert rules == []


def test_de_xuat_luat_tich_cuc_ton_kho() -> None:
    patterns = [
        _pattern(SuccessPatternType.TON_KHO_NHANH, 0.8, ["sua_tuoi"]),
    ]
    rules = de_xuat_luat_tich_cuc(patterns)
    assert len(rules) == 1
    assert rules[0].dieu_kien == {"nguyen_lieu": "sua_tuoi"}


def test_de_xuat_luat_tich_cuc_empty() -> None:
    assert de_xuat_luat_tich_cuc([]) == []