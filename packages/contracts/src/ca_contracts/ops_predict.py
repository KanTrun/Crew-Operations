"""Hợp đồng dữ liệu — Predictive Playbook & Digital Twin (NHỊP QUÁN OS Brain).

Nguồn: `plans/260918-nhip-quan-os-brain/plan.md` mục 3.

ADR-003 (contracts-first): module này phải tồn tại và có unit test validate TRƯỚC
khi bất kỳ logic nghiệp vụ nào của `ag_predict` / `ag_twin` được viết.

ADR-002 (tất định): contract chỉ mô tả hình dạng dữ liệu, không chứa suy luận
nghiệp vụ. Mọi con số (outlier dương, độ co giãn giá, phân rã mùa, doanh thu mô
phỏng) do tầng toán thuần ở `ca_agents.ag_predict.math_layer` sinh ra.

ADR-008 (con người quyết định): `PositiveRule` và `TwinScenario` là kênh GỢI Ý —
không có field nào mang nghĩa "thay đổi đã được áp dụng lên hệ thống thật".
Mọi luật tích cực phải đi qua vòng đời playbook và cần người duyệt.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# ── Enum nghiệp vụ (plan mục 3) ──────────────────────────────────────────────


class SuccessPatternType(StrEnum):
    """Loại mẫu thành công phát hiện từ dữ liệu lịch sử."""

    CA_DOANH_THU = "ca_doanh_thu"
    MON_BAN_CHAY = "mon_ban_chay"
    GIO_CAO_DIEM = "gio_cao_diem"
    TON_KHO_NHANH = "ton_kho_nhanh"


class SuccessPatternSource(StrEnum):
    """Nguồn dữ liệu phát hiện mẫu thành công."""

    LICH_SU_DOANH_THU = "lich_su_doanh_thu"
    LICH_SU_BAN = "lich_su_ban"
    TON_KHO = "ton_kho"
    FEEDBACK = "feedback"


class PositiveRuleStatus(StrEnum):
    """Trạng thái vòng đời luật tích cực (plan mục 3.2)."""

    DE_XUAT = "de_xuat"
    QUA_VF_RULE = "qua_vf_rule"
    DU_TAP_SU = "du_tap_su"
    HIEU_LUC = "hieu_luc"
    TU_CHOI = "tu_choi"
    DA_GO = "da_go"


class TwinScenarioType(StrEnum):
    """Loại kịch bản "nếu... thì..." cho digital twin (plan mục 3.3)."""

    TANG_GIA = "tang_gia"
    GIAM_GIA = "giam_gia"
    THEM_NHAN_SU = "them_nhan_su"
    BOT_NHAN_SU = "bot_nhan_su"
    DOI_GIO_MO_CUA = "doi_gio_mo_cua"


# ── Contract (plan mục 3.1–3.4) ──────────────────────────────────────────────


class SuccessPattern(BaseModel):
    """Mẫu thành công phát hiện từ dữ liệu lịch sử (tất định)."""

    pattern_id: str
    loai: SuccessPatternType
    mo_ta: str
    do_tin_cay: float = Field(ge=0.0)
    bang_chung: list[str] = Field(default_factory=list)
    nguon: SuccessPatternSource

    @field_validator("do_tin_cay")
    @classmethod
    def _clamp_do_tin_cay(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class PositiveRule(BaseModel):
    """Luật tích cực đề xuất từ mẫu thành công (plan mục 3.2)."""

    id: str
    cau: str
    dieu_kien: dict[str, object] = Field(default_factory=dict)
    bang_chung: list[str] = Field(default_factory=list)
    do_tin_cay: float = Field(ge=0.0)
    trang_thai: PositiveRuleStatus = PositiveRuleStatus.DE_XUAT

    @field_validator("do_tin_cay")
    @classmethod
    def _clamp_do_tin_cay(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class TwinScenario(BaseModel):
    """Kịch bản "nếu... thì..." cho digital twin (plan mục 3.3)."""

    scenario_id: str
    loai: TwinScenarioType
    tham_so: dict[str, object] = Field(default_factory=dict)
    baseline: dict[str, object] = Field(default_factory=dict)
    ket_qua: dict[str, object] = Field(default_factory=dict)
    rui_ro: str = ""


class PredictResponse(BaseModel):
    """Phản hồi tổng hợp cho dashboard đề xuất thông minh (plan mục 3.4)."""

    suggestions: list[PositiveRule] = Field(default_factory=list)
    patterns: list[SuccessPattern] = Field(default_factory=list)
    twin_scenarios: list[TwinScenario] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)