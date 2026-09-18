"""AG-PREDICT — Đề xuất luật tích cực từ mẫu thành công (plan mục 2.2, Phase 2).

Tái sử dụng vòng đời playbook 8 bước (`ca_playbook.vong_doi`). Luật tích cực
đi qua: de_xuat → qua_vf_rule → du_tap_su → hieu_luc. Fail-closed: chỉ đề xuất,
không tự áp dụng (ADR-008).
"""

from __future__ import annotations

from ca_contracts.ops_predict import (
    PositiveRule,
    PositiveRuleStatus,
    SuccessPattern,
    SuccessPatternType,
)

# Ngưỡng do_tin_cay tối thiểu để đề xuất — plan mục 13.2.
_MIN_DO_TIN_CAY = 0.5


def _cau_tu_pattern(pattern: SuccessPattern) -> str:
    """Dựng câu luật tích cực từ mẫu thành công (tất định)."""
    if pattern.loai == SuccessPatternType.CA_DOANH_THU:
        return f"Tăng cường nhân sự cho ca {pattern.bang_chung[0] if pattern.bang_chung else 'ca cao điểm'} do doanh thu vượt trội"
    if pattern.loai == SuccessPatternType.MON_BAN_CHAY:
        return f"Ưu tiên nguyên liệu và quảng bá món {pattern.bang_chung[0] if pattern.bang_chung else 'bán chạy'} do doanh thu cao"
    if pattern.loai == SuccessPatternType.TON_KHO_NHANH:
        return f"Tăng dự trữ nguyên liệu {pattern.bang_chung[0] if pattern.bang_chung else 'tiêu thụ nhanh'} để tránh hết hàng"
    return f"Nhân rộng mẫu thành công: {pattern.mo_ta}"


def _dieu_kien_tu_pattern(pattern: SuccessPattern) -> dict[str, object]:
    """Dựng điều kiện máy đọc được từ mẫu thành công."""
    if pattern.loai == SuccessPatternType.CA_DOANH_THU and pattern.bang_chung:
        return {"ca": pattern.bang_chung[0]}
    if pattern.loai == SuccessPatternType.MON_BAN_CHAY and pattern.bang_chung:
        return {"mon": pattern.bang_chung[0]}
    if pattern.loai == SuccessPatternType.TON_KHO_NHANH and pattern.bang_chung:
        return {"nguyen_lieu": pattern.bang_chung[0]}
    return {}


def de_xuat_luat_tich_cuc(
    patterns: list[SuccessPattern],
    *,
    min_do_tin_cay: float = _MIN_DO_TIN_CAY,
) -> list[PositiveRule]:
    """Đề xuất luật tích cực từ các mẫu thành công (fail-closed).

    Chỉ đề xuất khi mẫu có do_tin_cay >= ngưỡng. Không tự áp dụng.
    """
    rules: list[PositiveRule] = []
    for i, pattern in enumerate(patterns):
        if pattern.do_tin_cay < min_do_tin_cay:
            continue
        rules.append(
            PositiveRule(
                id=f"pos_rule_{i + 1}",
                cau=_cau_tu_pattern(pattern),
                dieu_kien=_dieu_kien_tu_pattern(pattern),
                bang_chung=pattern.bang_chung,
                do_tin_cay=pattern.do_tin_cay,
                trang_thai=PositiveRuleStatus.DE_XUAT,
            )
        )
    return rules