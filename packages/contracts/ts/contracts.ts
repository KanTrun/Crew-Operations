// Sinh tự động từ JSON Schema của pydantic — chạy `make contracts`.
// KHÔNG sửa tay: nguồn sự thật là packages/contracts/src/ca_contracts.

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export interface NhanVien {
  id: string;
  ten: string;
  ky_nang?: string[];
  la_sinh_vien?: boolean;
  so_dien_thoai_hash?: string | null;
}

export interface Ca {
  id: string;
  ngay: string;
  bat_dau: string;
  ket_thuc: string;
  vi_tri: string;
  so_nguoi_toi_thieu?: number;
}

export interface LichTuan {
  tuan_iso: string;
  trang_thai?: "nhap" | "dang_giai" | "cho_duyet" | "da_cong_bo" | "da_dong";
  phan_cong?: Record<string, string[]>;
}

export type MinhChungLoai = "khong" | "so" | "anh" | "kiem_ke" | "van_ban" | "danh_sach" | "xac_nhan" | "xac_nhan_doc";
export interface PhieuBuoc { ma: string; ten: string; minh_chung?: MinhChungLoai; }
export interface PhieuMau { ma: string; ten: string; gan_voi?: string | null; buoc: PhieuBuoc[]; }
export interface RangBuocTrichXuat { id: string; nguon: "tkb" | "tin_nhan" | "ban_giao" | "khac"; nhan_vien_id?: string | null; noi_dung: string; do_tin_cay: number; trang_thai?: "cho_duyet" | "da_duyet" | "tu_choi"; khung_gio?: string[]; }
export interface MonNuoc { id: string; ten: string; gia: number; an?: boolean; hinh_url?: string; bom?: Record<string, number>; }
export interface DongDon { mon_id: string; ten: string; so_luong: number; gia: number; }
export interface DonQuay { id: string; nv_id: string; trang_thai?: "cho_pha" | "dang_pha" | "xong" | "huy"; thanh_toan?: "tien_mat" | "da_ck" | "chua_thu"; dong: DongDon[]; ly_do_huy?: string | null; nguon?: string; luc?: string; }
export interface ActionItem { id: string; tieu_de: string; noi_dung_chi_tiet?: string; tinh_chat?: "bat_buoc" | "tuy_chon" | "khuyen_khich"; ten_nguoi_giao?: string; nhan_vien_id?: string | null; ten_nguoi_nhan: string; pham_vi?: "ca_nhan" | "nhom"; thoi_gian_bat_dau?: string; han_chot?: string; muc_do_uu_tien?: "cao" | "trung_binh" | "thap"; do_tin_cay?: number; da_chon?: boolean; }
export interface DeXuatPheDuyet { id: string; loai_de_xuat?: "quy_trinh_sop" | "mua_sam_vat_tu" | "chinh_sach_nhan_su" | "khac"; tieu_de: string; nguoi_de_xuat?: string; nguoi_phe_duyet?: string; noi_dung: string; ly_do?: string; trang_thai?: "da_duyet" | "cho_duyet" | "tu_choi"; quy_trinh_lien_quan?: string | null; buoc_so?: number | null; }
export interface DeXuatSop { quy_trinh_lien_quan: string; buoc_so?: number | null; noi_dung_thay_doi: string; ly_do?: string; }
export interface GopYLuuY { id: string; nguoi_gop_y?: string; nguoi_nhan?: string; chu_de?: "thai_do_phuc_vu" | "ky_nang_pha_che" | "ve_sinh_an_toan" | "dong_vien_khen_ngoi" | "luu_y_chung"; tinh_chat?: "nhac_nho" | "khen_ngoi" | "kinh_nghiem" | "gop_y"; noi_dung: string; ghi_chu?: string; }
export interface AuditTuanThuSop { diem_tuan_thu?: number; xep_hang?: "A" | "B" | "C" | "D"; tieu_chi?: TieuChiAudit[]; canh_bao_do?: string[]; nhan_xet_chung?: string; }
export interface TieuChiAudit { ma: string; ten_tieu_chi: string; dat?: boolean; chi_tiet?: string; }
export interface BanTinCaKhan { ban_vip?: string[]; luu_y_di_ung_khach?: string[]; su_co_thiet_bi_khan?: string[]; danh_sach_mon_86?: string[]; noi_dung_tin_nhan_gui_nhom?: string; }
export interface HuanLuyenQuanLy { ty_le_noi_quan_ly_pct?: number; ty_le_noi_nhan_vien_pct?: number; diem_tuong_tac_2_chieu?: number; diem_truyen_cam_hung?: number; phong_cach_dieu_hanh?: string; loi_khuyen_ai_coaching?: string[]; }
export interface DoanThoaiTranscript { nguoi_noi: string; bat_dau_s?: number | null; ket_thuc_s?: number | null; noi_dung: string; }
export interface CuocHop { id: string; tieu_de: string; loai_hop?: "giao_ca" | "hop_tuan" | "dao_tao" | "khac"; thoi_gian?: string; nguon_am_thanh?: "google_meet_tab" | "microphone" | "file_upload" | "ghi_chep_tay"; transcript_thoai?: DoanThoaiTranscript[]; tom_tat: string; quyet_dinh?: string[]; de_xuat_phe_duyet?: DeXuatPheDuyet[]; action_items?: ActionItem[]; gop_y_luu_y?: GopYLuuY[]; audit_sop?: AuditTuanThuSop | null; ban_tin_ca?: BanTinCaKhan | null; huan_luyen_quan_ly?: HuanLuyenQuanLy | null; de_xuat_sop?: DeXuatSop[]; do_tin_cay_tong_the?: number; trang_thai?: "cho_duyet" | "da_duyet" | "tu_choi"; }
export interface CopilotContext { store_id?: string; user_id: string; user_role: "chu_quan" | "quan_ly" | "nhan_vien"; active_date: string; channel?: "web" | "telegram" | "zalo"; recent_messages?: string[]; }
export interface CopilotMessage { message: string; context: CopilotContext; }
export type ActionProposalStatus = "draft" | "ready_for_approval" | "executing" | "executed" | "execution_failed" | "rejected" | "expired" | "stale_rejected";
export type CopilotIntent = "SCHEDULE_SOLVE" | "APPROVE_SHIFT_SWAP" | "GENERATE_DAILY_BRIEF" | "QUERY_SOP" | "ANALYZE_WASTE" | "CREATE_RULE_PROPOSAL" | "INVENTORY_RESTOCK_CHECK" | "SEND_MAIL" | "OUT_OF_SCOPE";

export interface ActionProposal {
  action_id: string;
  intent: CopilotIntent;
  status?: ActionProposalStatus;
  summary: string;
  explanation?: string;
  payload_diff?: Record<string, JsonValue>;
  requires_confirmation?: boolean;
  store_id?: string;
  created_by: string;
  confidence?: number;
  data_snapshot_hash?: string;
  expires_at: string;
  created_at?: string;
  executed_at?: string | null;
  amended_from?: string | null;
}

export type FbPolicyAction = "auto_send" | "queue_review" | "priority_review" | "escalate_owner" | "block_polite" | "block_silent";

export interface PolicyDecision {
  action: FbPolicyAction;
  reason: string;
  intent: string;
  confidence: number;
  assigned_role?: "quan_ly" | "chu_quan" | null;
  sla_minutes?: number | null;
  flagged_reasons?: string[];
}

