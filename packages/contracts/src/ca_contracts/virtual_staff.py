"""Hợp đồng dữ liệu — Virtual Staff (Generative Agents).

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 5 (Stanford, Park et al. 2023).

ADR-003 (contracts-first): module này phải tồn tại và có unit test validate TRƯỚC
khi bất kỳ logic nghiệp vụ nào được viết.

ADR-002 (tất định): mô phỏng hành vi nhân viên ảo dựa trên luật tất định, không LLM.

ADR-008 (con người quyết định): nhân viên ảo chỉ MÔ PHỎNG, không thay đổi hệ thống thật.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class VirtualStaffType(StrEnum):
    """Loại nhân viên ảo."""

    PHA_CHE = "pha_che"
    PHUC_VU = "phuc_vu"
    THU_NGAN = "thu_ngan"
    QUAN_LY = "quan_ly"


class VirtualStaff(BaseModel):
    """Một nhân viên ảo có tính cách, kỹ năng, lịch sử."""

    staff_id: str
    ten: str
    loai: VirtualStaffType
    ky_nang: list[str] = Field(default_factory=list)
    tinh_cach: str = ""
    lich_su: list[str] = Field(default_factory=list)


class VirtualSimulation(BaseModel):
    """Kết quả mô phỏng hành vi nhân viên ảo."""

    simulation_id: str
    kich_ban: str
    staff: list[VirtualStaff] = Field(default_factory=list)
    su_kien: list[str] = Field(default_factory=list)
    ket_luan: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)