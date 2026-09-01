"""Shared data contracts — Sprint-1 schemas plus quầy nội bộ (ADR-013)."""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


from typing import Any, Literal

from pydantic import BaseModel, Field


class NhanVien(BaseModel):
    id: str
    ten: str
    ky_nang: list[str] = Field(default_factory=list)
    la_sinh_vien: bool = True
    so_dien_thoai_hash: str | None = None


class Ca(BaseModel):
    id: str
    ngay: str
    bat_dau: str
    ket_thuc: str
    vi_tri: str
    so_nguoi_toi_thieu: int = 1


class LichTuan(BaseModel):
    tuan_iso: str
    trang_thai: Literal["nhap", "dang_giai", "cho_duyet", "da_cong_bo", "da_dong"] = "nhap"
    phan_cong: dict[str, list[str]] = Field(
        default_factory=dict,
        description="ca_id -> danh sách nhan_vien_id",
    )


class MinhChungLoai(StrEnum):
    khong = "khong"
    so = "so"
    anh = "anh"
    kiem_ke = "kiem_ke"
    van_ban = "van_ban"
    danh_sach = "danh_sach"
    xac_nhan = "xac_nhan"
    xac_nhan_doc = "xac_nhan_doc"


class PhieuBuoc(BaseModel):
    ma: str
    ten: str
    minh_chung: MinhChungLoai = MinhChungLoai.khong


class PhieuMau(BaseModel):
    ma: str
    ten: str
    gan_voi: str | None = None
    buoc: list[PhieuBuoc]


class RangBuocTrichXuat(BaseModel):
    id: str
    nguon: Literal["tkb", "tin_nhan", "ban_giao", "khac"]
    nhan_vien_id: str | None = None
    noi_dung: str
    do_tin_cay: float = Field(ge=0.0, le=1.0)
    trang_thai: Literal["cho_duyet", "da_duyet", "tu_choi"] = "cho_duyet"
    khung_gio: list[str] = Field(default_factory=list)


class DongDon(BaseModel):
    mon_id: str
    ten: str
    so_luong: int = Field(ge=1)
    gia: int = Field(ge=0)


class MonNuoc(BaseModel):
    id: str
    ten: str
    gia: int = Field(ge=0, description="Đồng, số nguyên")
    an: bool = False
    hinh_url: str = Field(default="", max_length=500, description="URL ảnh món (hoặc /api/v1/menu/{id}/anh)")
    bom: dict[str, float] = Field(
        default_factory=dict,
        description="Nguyên liệu ước lượng khi hoàn thành đơn, vd cafe_g, sua_ml, ly",
    )


class DonQuay(BaseModel):
    id: str
    nv_id: str
    trang_thai: Literal["cho_pha", "dang_pha", "xong", "huy"] = "cho_pha"
    thanh_toan: Literal["tien_mat", "da_ck", "chua_thu"] = "chua_thu"
    dong: list[DongDon]
    ly_do_huy: str | None = None
    nguon: Literal["quay_noi_bo"] = "quay_noi_bo"
    luc: str = ""


class DoanThoaiTranscript(BaseModel):
    nguoi_noi: str
    bat_dau_s: float | None = None
    ket_thuc_s: float | None = None
    noi_dung: str


class ActionItem(BaseModel):
    id: str
    tieu_de: str
    noi_dung_chi_tiet: str = ""
    tinh_chat: Literal["bat_buoc", "tuy_chon", "khuyen_khich"] = "bat_buoc"
    ten_nguoi_giao: str = ""
    nhan_vien_id: str | None = None
    ten_nguoi_nhan: str
    pham_vi: Literal["ca_nhan", "nhom"] = "ca_nhan"
    thoi_gian_bat_dau: str = ""
    han_chot: str = ""
    muc_do_uu_tien: Literal["cao", "trung_binh", "thap"] = "trung_binh"
    do_tin_cay: float = Field(ge=0.0, le=1.0, default=0.9)
    da_chon: bool = True


class DeXuatPheDuyet(BaseModel):
    id: str
    loai_de_xuat: Literal["quy_trinh_sop", "mua_sam_vat_tu", "chinh_sach_nhan_su", "khac"] = (
        "quy_trinh_sop"
    )
    tieu_de: str
    nguoi_de_xuat: str = ""
    nguoi_phe_duyet: str = ""
    noi_dung: str
    ly_do: str = ""
    trang_thai: Literal["da_duyet", "cho_duyet", "tu_choi"] = "cho_duyet"
    quy_trinh_lien_quan: str | None = None
    buoc_so: int | None = None


class GopYLuuY(BaseModel):
    id: str
    nguoi_gop_y: str = ""
    nguoi_nhan: str = ""
    chu_de: Literal[
        "thai_do_phuc_vu",
        "ky_nang_pha_che",
        "ve_sinh_an_toan",
        "dong_vien_khen_ngoi",
        "luu_y_chung",
    ] = "luu_y_chung"
    tinh_chat: Literal["nhac_nho", "khen_ngoi", "kinh_nghiem", "gop_y"] = "gop_y"
    noi_dung: str
    ghi_chu: str = ""


class DeXuatSop(BaseModel):
    quy_trinh_lien_quan: str
    buoc_so: int | None = None
    noi_dung_thay_doi: str
    ly_do: str = ""


class TieuChiAudit(BaseModel):
    ma: str
    ten_tieu_chi: str
    dat: bool = False
    chi_tiet: str = ""


class AuditTuanThuSop(BaseModel):
    diem_tuan_thu: int = Field(ge=0, le=100, default=100)
    xep_hang: Literal["A", "B", "C", "D"] = "A"
    tieu_chi: list[TieuChiAudit] = Field(default_factory=list)
    canh_bao_do: list[str] = Field(default_factory=list)
    nhan_xet_chung: str = ""


class BanTinCaKhan(BaseModel):
    ban_vip: list[str] = Field(default_factory=list)
    luu_y_di_ung_khach: list[str] = Field(default_factory=list)
    su_co_thiet_bi_khan: list[str] = Field(default_factory=list)
    danh_sach_mon_86: list[str] = Field(default_factory=list)
    noi_dung_tin_nhan_gui_nhom: str = ""


class HuanLuyenQuanLy(BaseModel):
    ty_le_noi_quan_ly_pct: int = Field(ge=0, le=100, default=70)
    ty_le_noi_nhan_vien_pct: int = Field(ge=0, le=100, default=30)
    diem_tuong_tac_2_chieu: int = Field(ge=0, le=10, default=8)
    diem_truyen_cam_hung: int = Field(ge=0, le=10, default=8)
    phong_cach_dieu_hanh: str = "Chuẩn mực & Tương tác"
    loi_khuyen_ai_coaching: list[str] = Field(default_factory=list)


class CuocHop(BaseModel):
    id: str
    tieu_de: str
    loai_hop: Literal["giao_ca", "hop_tuan", "dao_tao", "khac"] = "giao_ca"
    thoi_gian: str = ""
    nguon_am_thanh: Literal["google_meet_tab", "microphone", "file_upload", "ghi_chep_tay"] = (
        "microphone"
    )
    transcript_thoai: list[DoanThoaiTranscript] = Field(default_factory=list)
    tom_tat: str
    quyet_dinh: list[str] = Field(default_factory=list)
    de_xuat_phe_duyet: list[DeXuatPheDuyet] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    gop_y_luu_y: list[GopYLuuY] = Field(default_factory=list)
    audit_sop: AuditTuanThuSop | None = None
    ban_tin_ca: BanTinCaKhan | None = None
    huan_luyen_quan_ly: HuanLuyenQuanLy | None = None
    de_xuat_sop: list[DeXuatSop] = Field(default_factory=list)
    do_tin_cay_tong_the: float = Field(ge=0.0, le=1.0, default=0.9)
    trang_thai: Literal["cho_duyet", "da_duyet", "tu_choi"] = "cho_duyet"


class CopilotIntent(StrEnum):
    SCHEDULE_SOLVE = "SCHEDULE_SOLVE"
    APPROVE_SHIFT_SWAP = "APPROVE_SHIFT_SWAP"
    GENERATE_DAILY_BRIEF = "GENERATE_DAILY_BRIEF"
    QUERY_SOP = "QUERY_SOP"
    ANALYZE_WASTE = "ANALYZE_WASTE"
    CREATE_RULE_PROPOSAL = "CREATE_RULE_PROPOSAL"
    INVENTORY_RESTOCK_CHECK = "INVENTORY_RESTOCK_CHECK"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


# ── Ma trận quyền Role → Intent (single source of truth) ─────────────────────
# Nguyên tắc: fail-closed — intent không liệt kê = không ai được gọi.
# - nhan_vien: chỉ tra cứu/đọc (daily brief, SOP, hao hụt của chính mình).
# - quan_ly: + xếp lịch, duyệt đổi ca, đề xuất luật, kiểm kê tồn kho.
# - chu_quan: toàn bộ quyền quan_ly (không có intent riêng vượt quan_ly).
COPILOT_ROLE_INTENT_MATRIX: dict[str, frozenset[str]] = {
    "nhan_vien": frozenset(
        {
            "GENERATE_DAILY_BRIEF",
            "QUERY_SOP",
            "ANALYZE_WASTE",
            "OUT_OF_SCOPE",
        }
    ),
    "quan_ly": frozenset(
        {
            "GENERATE_DAILY_BRIEF",
            "QUERY_SOP",
            "ANALYZE_WASTE",
            "OUT_OF_SCOPE",
            "SCHEDULE_SOLVE",
            "APPROVE_SHIFT_SWAP",
            "CREATE_RULE_PROPOSAL",
            "INVENTORY_RESTOCK_CHECK",
        }
    ),
    "chu_quan": frozenset(
        {
            "GENERATE_DAILY_BRIEF",
            "QUERY_SOP",
            "ANALYZE_WASTE",
            "OUT_OF_SCOPE",
            "SCHEDULE_SOLVE",
            "APPROVE_SHIFT_SWAP",
            "CREATE_RULE_PROPOSAL",
            "INVENTORY_RESTOCK_CHECK",
        }
    ),
}


def copilot_intents_allowed_for_role(role: str) -> frozenset[str]:
    """Trả về tập intent được phép cho role. Fail-closed: role lạ → rỗng."""
    return COPILOT_ROLE_INTENT_MATRIX.get(role, frozenset())


def copilot_role_can_use_intent(role: str, intent: str) -> bool:
    """Kiểm tra role có được dùng intent không. Fail-closed."""
    return intent in copilot_intents_allowed_for_role(role)


class ActionProposalStatus(StrEnum):
    draft = "draft"
    ready_for_approval = "ready_for_approval"
    executed = "executed"
    rejected = "rejected"
    expired = "expired"
    stale_rejected = "stale_rejected"


class CopilotContext(BaseModel):
    store_id: str = "quan_01"
    user_id: str
    user_role: Literal["chu_quan", "quan_ly", "nhan_vien"]
    active_date: str
    channel: Literal["web", "telegram", "zalo"] = "web"
    recent_messages: list[str] = Field(default_factory=list, max_length=3)


class CopilotMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    context: CopilotContext


class ActionProposal(BaseModel):
    action_id: str
    intent: CopilotIntent
    status: ActionProposalStatus = ActionProposalStatus.draft
    summary: str
    explanation: str = ""
    payload_diff: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = True
    store_id: str = "quan_01"
    created_by: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    data_snapshot_hash: str = ""
    expires_at: str
    created_at: str = ""
    executed_at: str | None = None
    amended_from: str | None = None


class CopilotResponse(BaseModel):
    reply_text: str
    intent: CopilotIntent
    confidence: float = Field(ge=0.0, le=1.0)
    action_proposal: ActionProposal | None = None
    direct_answer: str | None = None
    citations: list[str] = Field(default_factory=list)


CONTRACTS = {
    "NhanVien": NhanVien,
    "Ca": Ca,
    "LichTuan": LichTuan,
    "PhieuMau": PhieuMau,
    "RangBuocTrichXuat": RangBuocTrichXuat,
    "MonNuoc": MonNuoc,
    "DonQuay": DonQuay,
    "DongDon": DongDon,
    "CuocHop": CuocHop,
    "ActionItem": ActionItem,
    "DeXuatSop": DeXuatSop,
    "DeXuatPheDuyet": DeXuatPheDuyet,
    "GopYLuuY": GopYLuuY,
    "AuditTuanThuSop": AuditTuanThuSop,
    "BanTinCaKhan": BanTinCaKhan,
    "HuanLuyenQuanLy": HuanLuyenQuanLy,
    "CopilotMessage": CopilotMessage,
    "ActionProposal": ActionProposal,
}

