"""VF-RULE — ≥3 evidence, existing fields only, no person-targeted rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LOAI_HOP_LE = (
    "nhu_cau_ca",
    "nguong_ton",
    "buoc_phieu",
    "ghep_ky_nang",
    "hao_hut",
)

DEFAULT_FIELDS = {
    "thu",
    "khung",
    "vi_tri",
    "so_nguoi",
    "nguong",
    "ma_buoc",
    "thang_kinh_nghiem",
}


@dataclass
class RuleResult:
    passed: bool
    loai: str = ""
    reason: str = ""


def validate_rule(luat: dict[str, Any], *, fields: set[str] | None = None) -> RuleResult:
    loai = str(luat.get("loai") or "")
    if loai not in LOAI_HOP_LE:
        return RuleResult(passed=False, loai=loai, reason="loai_khong_hop_le")
    bang = luat.get("bang_chung") or []
    if len(bang) < 3:
        return RuleResult(passed=False, loai=loai, reason="thieu_bang_chung")
    cau = str(luat.get("cau") or "").lower()
    if any(k.strip() and k in cau for k in ("lười", "luoi", "thái độ", "thai do")):
        return RuleResult(passed=False, loai=loai, reason="luat_ve_nguoi")
    dieu = luat.get("dieu_kien") or {}
    if not isinstance(dieu, dict):
        return RuleResult(passed=False, loai=loai, reason="dieu_kien_khong_cau_truc")
    known = fields if fields is not None else DEFAULT_FIELDS
    extra = set(dieu) - known
    if extra:
        return RuleResult(passed=False, loai=loai, reason=f"truong_khong_ton_tai:{sorted(extra)}")
    return RuleResult(passed=True, loai=loai)
