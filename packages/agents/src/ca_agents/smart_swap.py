"""Smart Shift Swap & Emergency Leave Matching Engine (AG-SWAP).

Thuật toán ghép ứng viên đổi ca và tìm người bù ca khẩn cấp theo:
1. Kỹ năng chuyên môn (Skill Qualification).
2. Thời gian rảnh (Availability).
3. Ràng buộc Cẩm nang quán (Playbook Rules: max ca liên tục, max giờ tuần).
4. Độ công bằng (Fairness Debt & Shift Count).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SwapCandidate:
    nv_id: str
    ten: str
    score: int  # 0 to 100
    is_qualified: bool
    is_available: bool
    consecutive_shifts_today: int
    weekly_shift_count: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nv_id": self.nv_id,
            "ten": self.ten,
            "score": self.score,
            "is_qualified": self.is_qualified,
            "is_available": self.is_available,
            "consecutive_shifts_today": self.consecutive_shifts_today,
            "weekly_shift_count": self.weekly_shift_count,
            "reasons": self.reasons,
            "warnings": self.warnings,
        }


# Thứ tự khung ca trong ngày để kiểm tra ca liền kề
KHUNG_ORDER = ("sang", "chieu", "toi")


def _is_adjacent(khung1: str, khung2: str) -> bool:
    if khung1 not in KHUNG_ORDER or khung2 not in KHUNG_ORDER:
        return False
    idx1 = KHUNG_ORDER.index(khung1)
    idx2 = KHUNG_ORDER.index(khung2)
    return abs(idx1 - idx2) == 1


def find_swap_candidates(
    requester_id: str,
    ca_id: str | None = None,
    shift_info: dict[str, Any] | None = None,
    staff_list: list[dict[str, Any]] | None = None,
    ca_list: list[dict[str, Any]] | None = None,
    phan_cong: dict[str, list[str]] | None = None,
    max_ca_lien_tuc: int = 2,
) -> list[SwapCandidate]:
    """Tìm và xếp hạng các nhân viên phù hợp nhất để nhận/đổi ca.

    Args:
        requester_id: ID nhân viên cần đổi/xin nghỉ.
        ca_id: ID ca làm việc (nếu có).
        shift_info: Thông tin ca {thu, khung, vi_tri} nếu không có ca_id.
        staff_list: Danh sách hồ sơ nhân viên quán.
        ca_list: Danh mục các ca làm việc trong tuần.
        phan_cong: Bảng phân công hiện tại {ca_id: [nv_id1, nv_id2]}.
        max_ca_lien_tuc: Giới hạn ca liên tiếp trong ngày theo cẩm nang (mặc định: 2).
    """
    staffs = staff_list or []
    shifts = ca_list or []
    assignments = phan_cong or {}

    # 1. Xác định thông tin ca mục tiêu
    target_shift: dict[str, Any] = {}
    if ca_id:
        found_ca = next((c for c in shifts if c.get("id") == ca_id), None)
        if found_ca:
            target_shift = dict(found_ca)

    if not target_shift and shift_info:
        target_shift = dict(shift_info)

    target_thu = str(target_shift.get("thu") or "")
    target_khung = str(target_shift.get("khung") or "")
    target_vi_tri = str(target_shift.get("vi_tri") or "")

    # Đếm số ca của từng nhân viên trong tuần để tính công bằng
    weekly_counts: dict[str, int] = {}
    for assigned_nvs in assignments.values():
        for nid in assigned_nvs:
            weekly_counts[nid] = weekly_counts.get(nid, 0) + 1

    avg_shifts = (sum(weekly_counts.values()) / max(1, len(staffs))) if staffs else 3.0

    candidates: list[SwapCandidate] = []

    for s in staffs:
        nid = str(s.get("id") or s.get("nv_id") or "")
        ten = str(s.get("ten") or s.get("display_name") or nid)
        if not nid or nid == requester_id:
            continue

        skills = [str(k).lower() for k in (s.get("ky_nang") or s.get("skills") or [])]
        is_qualified = (not target_vi_tri) or (target_vi_tri.lower() in skills)

        # 2. Kiểm tra tính khả dụng (Availability)
        # Xem nhân viên này có đang làm ca nào khác vào cùng thứ và cùng khung giờ không
        is_busy_same_slot = False
        shifts_today: list[dict[str, Any]] = []

        for c in shifts:
            cid = str(c.get("id") or "")
            c_thu = str(c.get("thu") or "")
            c_khung = str(c.get("khung") or "")

            if nid in assignments.get(cid, []):
                if c_thu == target_thu:
                    shifts_today.append(c)
                    if c_khung == target_khung:
                        is_busy_same_slot = True

        is_available = not is_busy_same_slot

        # 3. Kiểm tra Cẩm nang: Ca liên tiếp trong ngày
        reasons: list[str] = []
        warnings: list[str] = []
        consecutive_today = len(shifts_today)
        violates_consecutive = False

        if is_available and shifts_today:
            # Kiểm tra xem có tạo thành chuỗi ca vượt ngưỡng max_ca_lien_tuc không
            for existing_c in shifts_today:
                ex_khung = str(existing_c.get("khung") or "")
                if _is_adjacent(ex_khung, target_khung):
                    consecutive_today += 1
                    warnings.append(f"Làm ca {ex_khung} liền kề trên cùng ngày {target_thu}")

            if consecutive_today > max_ca_lien_tuc:
                violates_consecutive = True
                warnings.append(f"Vượt giới hạn Cẩm nang: tối đa {max_ca_lien_tuc} ca liên tiếp/ngày")

        # 4. Chấm điểm độ phù hợp (Score 0 - 100)
        score = 0
        if not is_qualified or not is_available:
            score = 0
        elif violates_consecutive:
            score = 25  # Khả dĩ nhưng vi phạm cẩm nang
        else:
            # Điểm cơ sở khi đủ điều kiện & rảnh
            score = 60

            # Điểm cộng kỹ năng
            if target_vi_tri and target_vi_tri.lower() in skills:
                score += 15
                reasons.append(f"Đúng kỹ năng chuyên môn ({target_vi_tri})")

            if is_available:
                reasons.append(f"Đang rảnh khung {target_khung} {target_thu}")

            # Điểm công bằng: Ưu tiên người làm ít ca hơn mức trung bình
            w_count = weekly_counts.get(nid, 0)
            if w_count < avg_shifts:
                bonus = int(min(20, (avg_shifts - w_count) * 10))
                score += bonus
                reasons.append(f"Tuần này mới làm {w_count} ca (ít hơn trung bình)")
            elif w_count == 0:
                score += 20
                reasons.append("Chưa có ca làm việc nào trong tuần")
            else:
                reasons.append(f"Đã phân {w_count} ca trong tuần")

            # Trừ nhẹ nếu có ca liền kề nhưng chưa vi phạm
            if len(shifts_today) > 0 and not violates_consecutive:
                score = max(40, score - 10)

        cand = SwapCandidate(
            nv_id=nid,
            ten=ten,
            score=min(100, max(0, score)),
            is_qualified=is_qualified,
            is_available=is_available,
            consecutive_shifts_today=consecutive_today,
            weekly_shift_count=weekly_counts.get(nid, 0),
            reasons=reasons,
            warnings=warnings,
        )
        candidates.append(cand)

    # Sắp xếp ưu tiên: đủ điều kiện -> điểm cao -> số ca tuần ít
    candidates.sort(
        key=lambda c: (c.is_qualified and c.is_available, c.score, -c.weekly_shift_count),
        reverse=True,
    )
    return candidates


def find_emergency_cover_candidates(
    absent_staff_id: str,
    ca_id: str | None = None,
    shift_info: dict[str, Any] | None = None,
    staff_list: list[dict[str, Any]] | None = None,
    ca_list: list[dict[str, Any]] | None = None,
    phan_cong: dict[str, list[str]] | None = None,
) -> list[SwapCandidate]:
    """Tìm nhân sự dự phòng bù ca khẩn cấp (trong ngày / dưới 24h)."""
    base_cands = find_swap_candidates(
        requester_id=absent_staff_id,
        ca_id=ca_id,
        shift_info=shift_info,
        staff_list=staff_list,
        ca_list=ca_list,
        phan_cong=phan_cong,
        max_ca_lien_tuc=2,
    )
    # Với ca khẩn, ưu tiên người có thể gọi điện trực tiếp
    emergency_list = []
    for c in base_cands:
        if c.is_qualified and c.is_available:
            emergency_list.append(c)
    return emergency_list if emergency_list else base_cands


def format_swap_recommendation(
    requester_name: str,
    target_ca_label: str,
    candidates: list[SwapCandidate],
    is_emergency: bool = False,
) -> str:
    """Soạn lời tư vấn gợi ý đổi ca chuẩn xác và lịch sự."""
    if not candidates or candidates[0].score == 0:
        return (
            f"Dạ hệ thống đã kiểm tra nhưng hiện tại chưa tìm thấy bạn nào rảnh và đúng chuyên môn "
            f"cho ca {target_ca_label}. Em đã gửi yêu cầu lên Quản lý để hỗ trợ sắp xếp nhé ạ!"
        )

    top = [c for c in candidates if c.score >= 50][:2]
    if not top:
        top = [candidates[0]]

    lines = []
    prefix = "🚨 YÊU CẦU BÙ CA KHẨN CẤP:" if is_emergency else "💡 GỢI Ý ĐỔI CA THÔNG MINH:"
    lines.append(f"{prefix}")
    lines.append(f"Hệ thống đề xuất các bạn có thể nhận ca {target_ca_label} hỗ trợ {requester_name}:")

    for i, c in enumerate(top, 1):
        star = "⭐ " if i == 1 else ""
        reason_str = ", ".join(c.reasons[:2]) if c.reasons else "Đang rảnh"
        warn_str = f" (Lưu ý: {c.warnings[0]})" if c.warnings else ""
        lines.append(f"{i}. {star}{c.ten} ({c.score}%) — {reason_str}{warn_str}")

    lines.append("Yêu cầu đã được tự động điền sẵn ứng viên và gửi Quản lý phê duyệt 1-chạm.")
    return "\n".join(lines)
