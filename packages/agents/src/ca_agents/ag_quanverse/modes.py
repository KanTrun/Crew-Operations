"""Cafe Modes — đề xuất chế độ, không tự động ẩn.

Mọi mode activation là proposal → manager/owner confirm → mode emit scoped
event + read-only projection. Nhân viên không kích hoạt được.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ca_contracts import ExperienceMode, ExperienceProposalStatus
from ca_contracts.grand_experience import ExperienceRole


@dataclass
class ModeState:
    """Trạng thái mode trong store."""

    mode: ExperienceMode
    active: bool = False
    proposal_status: ExperienceProposalStatus | None = None
    proposed_by: str | None = None
    confirmed_by: str | None = None
    affected_projections: list[str] = field(default_factory=list)


def allowed_mode_activation_roles() -> frozenset[str]:
    return frozenset({ExperienceRole.QUAN_LY.value, ExperienceRole.CHU_QUAN.value})


def can_activate_mode(role: str) -> bool:
    return role in allowed_mode_activation_roles()


def mode_affects(mode: ExperienceMode) -> list[str]:
    """Projection mà mode này tác động (read-only, tất định)."""
    impact: dict[ExperienceMode, list[str]] = {
        ExperienceMode.TROI_MUA: ["khu_ngoai_troi", "khach_vao", "den_bao_mua"],
        ExperienceMode.GIO_CAO_DIEM: ["quay_pha_che", "thu_ngan", "nhan_su"],
        ExperienceMode.KHACH_DOAN: ["ban_lon", "kho", "dich_vu"],
        ExperienceMode.THIEU_NHAN_SU: ["nhan_su", "nang_luc", "crisis"],
        ExperienceMode.QUAN_YEN_TINH: ["khong_gian", "den", "nhac"],
        ExperienceMode.DEM_NHAC: ["am_nhac", "khong_gian", "bar"],
    }
    return impact.get(mode, [])


def mode_effect(mode: ExperienceMode) -> str:
    """Hệ quả vận hành khi bật mode — nói cho người duyệt biết mình đang đổi gì.

    Tách khỏi `mode_affects`: `affects` là mã projection cho máy, `effect` là câu
    người đọc. Cùng một nguồn sự thật nên không lệch nhau khi thêm mode mới.
    """
    effects: dict[ExperienceMode, str] = {
        ExperienceMode.TROI_MUA: "Dồn chỗ ngồi trong nhà, ưu tiên món nóng.",
        ExperienceMode.GIO_CAO_DIEM: "Bật gợi ý san ca và cảnh báo quầy quá tải.",
        ExperienceMode.KHACH_DOAN: "Gom bàn, chuẩn bị đón đoàn và xếp trước.",
        ExperienceMode.THIEU_NHAN_SU: "Mở luồng cứu ca và xếp hạng người bù.",
        ExperienceMode.QUAN_YEN_TINH: "Giảm nhạc, hạn chế thông báo không khẩn.",
        ExperienceMode.DEM_NHAC: "Bật lịch nhạc, giữ khu vực sân khấu.",
    }
    return effects.get(mode, "Thay đổi cách quán vận hành trong khung giờ tới.")