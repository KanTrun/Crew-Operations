// Auto-generated stub types — refine with openapi-typescript in S2

export type NhanVien = Record<string, unknown>;
export type Ca = Record<string, unknown>;
export type LichTuan = Record<string, unknown>;
export type PhieuMau = Record<string, unknown>;
export type RangBuocTrichXuat = Record<string, unknown>;

export interface DoanThoaiTranscript {
  nguoi_noi: string;
  bat_dau_s?: number;
  ket_thuc_s?: number;
  noi_dung: string;
}

export interface ActionItem {
  id: string;
  tieu_de: string;
  noi_dung_chi_tiet?: string;
  tinh_chat?: "bat_buoc" | "tuy_chon" | "khuyen_khich";
  ten_nguoi_giao?: string;
  nhan_vien_id?: string | null;
  ten_nguoi_nhan: string;
  pham_vi?: "ca_nhan" | "nhom";
  thoi_gian_bat_dau?: string;
  han_chot?: string;
  muc_do_uu_tien?: "cao" | "trung_binh" | "thap";
  do_tin_cay: number;
  da_chon?: boolean;
}

export interface DeXuatPheDuyet {
  id: string;
  loai_de_xuat: "quy_trinh_sop" | "mua_sam_vat_tu" | "chinh_sach_nhan_su" | "khac";
  tieu_de: string;
  nguoi_de_xuat?: string;
  nguoi_phe_duyet?: string;
  noi_dung: string;
  ly_do?: string;
  trang_thai: "da_duyet" | "cho_duyet" | "tu_choi";
  quy_trinh_lien_quan?: string | null;
  buoc_so?: number | null;
}

export interface DeXuatSop {
  quy_trinh_lien_quan: string;
  buoc_so?: number | null;
  noi_dung_thay_doi: string;
  ly_do?: string;
}

export interface GopYLuuY {
  id: string;
  nguoi_gop_y?: string;
  nguoi_nhan?: string;
  chu_de?: "thai_do_phuc_vu" | "ky_nang_pha_che" | "ve_sinh_an_toan" | "dong_vien_khen_ngoi" | "luu_y_chung";
  tinh_chat?: "nhac_nho" | "khen_ngoi" | "kinh_nghiem" | "gop_y";
  noi_dung: string;
  ghi_chu?: string;
}

export interface TieuChiAudit {
  ma: string;
  ten_tieu_chi: string;
  dat: boolean;
  chi_tiet?: string;
}

export interface AuditTuanThuSop {
  diem_tuan_thu: number;
  xep_hang: "A" | "B" | "C" | "D";
  tieu_chi: TieuChiAudit[];
  canh_bao_do?: string[];
  nhan_xet_chung?: string;
}

export interface BanTinCaKhan {
  ban_vip?: string[];
  luu_y_di_ung_khach?: string[];
  su_co_thiet_bi_khan?: string[];
  danh_sach_mon_86?: string[];
  noi_dung_tin_nhan_gui_nhom?: string;
}

export interface HuanLuyenQuanLy {
  ty_le_noi_quan_ly_pct: number;
  ty_le_noi_nhan_vien_pct: number;
  diem_tuong_tac_2_chieu: number;
  diem_truyen_cam_hung: number;
  phong_cach_dieu_hanh?: string;
  loi_khuyen_ai_coaching?: string[];
}

export interface CuocHop {
  id: string;
  tieu_de: string;
  loai_hop: "giao_ca" | "hop_tuan" | "dao_tao" | "khac";
  thoi_gian?: string;
  nguon_am_thanh?: "google_meet_tab" | "microphone" | "file_upload" | "ghi_chep_tay";
  transcript_thoai?: DoanThoaiTranscript[];
  tom_tat: string;
  quyet_dinh?: string[];
  de_xuat_phe_duyet?: DeXuatPheDuyet[];
  action_items: ActionItem[];
  gop_y_luu_y?: GopYLuuY[];
  audit_sop?: AuditTuanThuSop;
  ban_tin_ca?: BanTinCaKhan;
  huan_luyen_quan_ly?: HuanLuyenQuanLy;
  de_xuat_sop?: DeXuatSop[];
  do_tin_cay_tong_the?: number;
  trang_thai?: "cho_duyet" | "da_duyet" | "tu_choi";
}




