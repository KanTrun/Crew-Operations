"""AG-TWIN — Virtual Staff (Generative Agents) mô phỏng hành vi nhân viên.

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 5 (Stanford, Park et al. 2023).

ADR-002: mô phỏng hành vi dựa trên luật tất định (tải, kỹ năng, tính cách),
không LLM. Cùng input → cùng output.

ADR-008: chỉ mô phỏng, không thay đổi hệ thống thật.
"""

from __future__ import annotations

from typing import Any

from ca_contracts.virtual_staff import (
    VirtualSimulation,
    VirtualStaff,
    VirtualStaffType,
)

# Ngưỡng tải tối đa trước khi nhân viên ảo "quá tải"
_MAX_TAI = 3


def _build_staff(rows: list[dict[str, Any]]) -> list[VirtualStaff]:
    """Dựng danh sách nhân viên ảo từ dữ liệu thật (tất định)."""
    staff: list[VirtualStaff] = []
    for i, row in enumerate(rows):
        loai_raw = str(row.get("loai") or "pha_che")
        loai_map = {
            "pha_che": VirtualStaffType.PHA_CHE,
            "phuc_vu": VirtualStaffType.PHUC_VU,
            "thu_ngan": VirtualStaffType.THU_NGAN,
            "quan_ly": VirtualStaffType.QUAN_LY,
        }
        loai = loai_map.get(loai_raw, VirtualStaffType.PHA_CHE)
        staff.append(
            VirtualStaff(
                staff_id=str(row.get("id") or f"vs_{i + 1}"),
                ten=str(row.get("ten") or f"Nhân viên {i + 1}"),
                loai=loai,
                ky_nang=list(row.get("ky_nang") or []),
                tinh_cach=str(row.get("tinh_cach") or "bình thường"),
                lich_su=list(row.get("lich_su") or []),
            )
        )
    return staff


def _simulate_workload(
    staff: list[VirtualStaff],
    kich_ban: str,
    *,
    so_lan: int = 1,
) -> list[str]:
    """Mô phỏng khối lượng công việc cho từng nhân viên ảo (tất định).

    Mỗi nhân viên có tải = số món/khách giao. Nếu tải > _MAX_TAI → quá tải.
    """
    su_kien: list[str] = []
    # Ước tính tải từ kịch bản (số người trong ca)
    so_nguoi = 0
    for part in kich_ban.split():
        if part.isdigit():
            so_nguoi = int(part)
            break
    if so_nguoi == 0:
        so_nguoi = 2  # mặc định

    for _ in range(so_lan):
        for s in staff:
            tai = so_nguoi // max(1, len(staff))
            if tai > _MAX_TAI:
                su_kien.append(
                    f"{s.ten} ({s.loai.value}) bị quá tải: {tai} việc cùng lúc, phàn nàn"
                )
            else:
                su_kien.append(
                    f"{s.ten} ({s.loai.value}) xử lý {tai} việc, ổn định"
                )
    return su_kien


def simulate_virtual_staff(
    simulation_id: str,
    kich_ban: str,
    staff_rows: list[dict[str, Any]],
    *,
    so_lan: int = 1,
) -> VirtualSimulation:
    """Mô phỏng hành vi nhân viên ảo cho một kịch bản (tất định)."""
    staff = _build_staff(staff_rows)
    su_kien = _simulate_workload(staff, kich_ban, so_lan=so_lan)

    # Kết luận tất định
    qua_tai = [s for s in su_kien if "quá tải" in s]
    if qua_tai:
        ket_luan = f"Phát hiện {len(qua_tai)} nhân viên ảo quá tải. Kịch bản '{kich_ban}' có rủi ro."
    else:
        ket_luan = f"Kịch bản '{kich_ban}' khả thi: {len(staff)} nhân viên ảo xử lý ổn định."

    return VirtualSimulation(
        simulation_id=simulation_id,
        kich_ban=kich_ban,
        staff=staff,
        su_kien=su_kien,
        ket_luan=ket_luan,
    )