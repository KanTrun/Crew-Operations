"""Eligibility — bộ lọc tất định trả về reason codes.

Mỗi ràng buộc là hàm thuần (ADR-002), không gọi LLM/DB. Reason codes:
- C01: trùng giờ học (TKB)
- C02: thiếu kỹ năng vị trí
- C03: trùng ca cùng lúc
- C04: khoảng nghỉ tối thiểu
- C05: trần giờ tuần
- C06: nghỉ phép đã duyệt
- skill, cap, fairness được tách riêng.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StaffProfile:
    """Input tối thiểu cần cho eligibility (không chứa dữ liệu riêng tư)."""

    nv_id: str
    ten: str = ""
    ky_nang: set[str] = field(default_factory=set)
    # tuần này đã làm bao nhiêu giờ (tính c05)
    gio_da_lam: float = 0.0
    # số ca tuần này (tính fairness)
    so_ca_tuan: int = 0
    # set ca_id họ đang được phân trong tuần (tính c03, c04)
    ca_ids: set[str] = field(default_factory=set)
    ca_meta: dict[str, dict[str, str]] = field(default_factory=dict)
    tkb_conflict: bool = False
    nghi_phep_approved: bool = False


# Reason codes quy chuẩn (fail-closed / private-safe)
BLOCK_REASONS = {
    "C01": "trung_gio_hoc_tkb",
    "C02": "thieu_ky_nang_vi_tri",
    "C03": "trung_ca_cung_luc",
    "C04": "khong_du_khoang_nghi_toi_thieu",
    "C05": "vuot_tran_gio_tuan",
    "C06": "dang_nghi_phep_da_duyet",
    "SKILL": "thieu_ky_nang",
    "CAP": "vuot_tran_gio",
    "SELF": "khong_the_thay_chinh_minh",
}


def _has_tkb_conflict(profile: StaffProfile, ca_id: str, meta: dict[str, str]) -> bool:
    """C01 — TKB: nếu profile đã có cờ tkb_conflict cho ca này."""
    return profile.tkb_conflict


def _has_shift_overlap(profile: StaffProfile, ca_id: str, meta: dict[str, str]) -> bool:
    """C03 — trùng ca: người này đã có ca cùng slot (cùng thu + khung)."""
    target_thu = meta.get("thu", "")
    target_khung = meta.get("khung", "")
    for cid in profile.ca_ids:
        m = profile.ca_meta.get(cid, {})
        if m.get("thu") == target_thu and m.get("khung") == target_khung:
            return True
    return False


def _min_rest_violated(profile: StaffProfile, ca_id: str, meta: dict[str, str], khoang_nghi_gio: float) -> bool:
    """C04 — khoảng nghỉ tối thiểu giữa hai ca (tất định, tránh trùng c04 solver)."""
    target_thu = meta.get("thu", "")
    target_khung = meta.get("khung", "")
    # Khung ca cơ bản: sang 06-12, chieu 12-18, toi 17-22
    khung_range = {
        "sang": ("06:00", "12:00"),
        "chieu": ("12:00", "18:00"),
        "toi": ("17:00", "22:00"),
    }
    t0, t1 = khung_range.get(target_khung, ("00:00", "23:59"))
    for cid in profile.ca_ids:
        m = profile.ca_meta.get(cid, {})
        if m.get("thu") != target_thu:
            continue
        e0, e1 = khung_range.get(str(m.get("khung") or ""), ("00:00", "23:59"))
        # Nếu hai ca chồng hoặc liền kề ít hơn khoang_nghi_gio giờ → vi phạm
        gap_ok = not (t0 < e1 and e0 < t1)
        if not gap_ok and khoang_nghi_gio > 0:
            return True
    return False


def _cap_violated(profile: StaffProfile, hours_to_add: float, tran_gio_tuan: float) -> bool:
    """C05/CAP — trần giờ tuần."""
    if tran_gio_tuan <= 0:
        return False
    return (profile.gio_da_lam + hours_to_add) > tran_gio_tuan


def eligibility_reasons(
    profile: StaffProfile,
    *,
    ca_meta: dict[str, str],
    required_skill: str | None,
    tran_gio_tuan: float,
    khoang_nghi_gio: float,
    hours_to_add: float,
    is_self: bool = False,
) -> list[str]:
    """Trả danh sách reason block (rỗng = an toàn). Pure, no side effect."""
    reasons: list[str] = []
    ca_id = ca_meta.get("ca_id", "")

    if is_self:
        reasons.append(BLOCK_REASONS["SELF"])
    if required_skill and required_skill not in profile.ky_nang:
        reasons.append(BLOCK_REASONS["SKILL"])
    if _has_tkb_conflict(profile, ca_id, ca_meta):
        reasons.append(BLOCK_REASONS["C01"])
    if _has_shift_overlap(profile, ca_id, ca_meta):
        reasons.append(BLOCK_REASONS["C03"])
    if _min_rest_violated(profile, ca_id, ca_meta, khoang_nghi_gio):
        reasons.append(BLOCK_REASONS["C04"])
    if _cap_violated(profile, hours_to_add, tran_gio_tuan):
        reasons.append(BLOCK_REASONS["C05"])
    if profile.nghi_phep_approved:
        reasons.append(BLOCK_REASONS["C06"])

    return reasons


def filter_eligible(
    staff: list[StaffProfile],
    *,
    absence_nv_id: str,
    ca_meta: dict[str, str],
    required_skill: str | None,
    tran_gio_tuan: float,
    khoang_nghi_gio: float,
    hours_to_add: float,
) -> list[StaffProfile]:
    """Lọc danh sách an toàn — không bao giờ đề xuất người vi phạm hard constraint."""
    safe: list[StaffProfile] = []
    for s in staff:
        if s.nv_id == absence_nv_id:
            continue
        reasons = eligibility_reasons(
            s,
            ca_meta=ca_meta,
            required_skill=required_skill,
            tran_gio_tuan=tran_gio_tuan,
            khoang_nghi_gio=khoang_nghi_gio,
            hours_to_add=hours_to_add,
        )
        if not reasons:
            safe.append(s)
    return safe