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

export interface PhieuBuoc {
  ma: string;
  ten: string;
  minh_chung?: MinhChungLoai;
}

export interface PhieuMau {
  ma: string;
  ten: string;
  gan_voi?: string | null;
  buoc: PhieuBuoc[];
}

export interface RangBuocTrichXuat {
  id: string;
  nguon: "tkb" | "tin_nhan" | "ban_giao" | "khac";
  nhan_vien_id?: string | null;
  noi_dung: string;
  do_tin_cay: number;
  trang_thai?: "cho_duyet" | "da_duyet" | "tu_choi";
  khung_gio?: string[];
}

export interface MonNuoc {
  id: string;
  ten: string;
  gia: number;
  an?: boolean;
  hinh_url?: string;
  bom?: Record<string, number>;
}

export interface DongDon {
  mon_id: string;
  ten: string;
  so_luong: number;
  gia: number;
}

export interface DonQuay {
  id: string;
  nv_id: string;
  trang_thai?: "cho_pha" | "dang_pha" | "xong" | "huy";
  thanh_toan?: "tien_mat" | "da_ck" | "chua_thu";
  dong: DongDon[];
  ly_do_huy?: string | null;
  nguon?: string;
  luc?: string;
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
  do_tin_cay?: number;
  da_chon?: boolean;
}

export interface AuditTuanThuSop {
  diem_tuan_thu?: number;
  xep_hang?: "A" | "B" | "C" | "D";
  tieu_chi?: TieuChiAudit[];
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

export interface DeXuatPheDuyet {
  id: string;
  loai_de_xuat?: "quy_trinh_sop" | "mua_sam_vat_tu" | "chinh_sach_nhan_su" | "khac";
  tieu_de: string;
  nguoi_de_xuat?: string;
  nguoi_phe_duyet?: string;
  noi_dung: string;
  ly_do?: string;
  trang_thai?: "da_duyet" | "cho_duyet" | "tu_choi";
  quy_trinh_lien_quan?: string | null;
  buoc_so?: number | null;
}

export interface DeXuatSop {
  quy_trinh_lien_quan: string;
  buoc_so?: number | null;
  noi_dung_thay_doi: string;
  ly_do?: string;
}

export interface DoanThoaiTranscript {
  nguoi_noi: string;
  bat_dau_s?: number | null;
  ket_thuc_s?: number | null;
  noi_dung: string;
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

export interface HuanLuyenQuanLy {
  ty_le_noi_quan_ly_pct?: number;
  ty_le_noi_nhan_vien_pct?: number;
  diem_tuong_tac_2_chieu?: number;
  diem_truyen_cam_hung?: number;
  phong_cach_dieu_hanh?: string;
  loi_khuyen_ai_coaching?: string[];
}

export interface TieuChiAudit {
  ma: string;
  ten_tieu_chi: string;
  dat?: boolean;
  chi_tiet?: string;
}

export interface CuocHop {
  id: string;
  tieu_de: string;
  loai_hop?: "giao_ca" | "hop_tuan" | "dao_tao" | "khac";
  thoi_gian?: string;
  nguon_am_thanh?: "google_meet_tab" | "microphone" | "file_upload" | "ghi_chep_tay";
  transcript_thoai?: DoanThoaiTranscript[];
  tom_tat: string;
  quyet_dinh?: string[];
  de_xuat_phe_duyet?: DeXuatPheDuyet[];
  action_items?: ActionItem[];
  gop_y_luu_y?: GopYLuuY[];
  audit_sop?: AuditTuanThuSop | null;
  ban_tin_ca?: BanTinCaKhan | null;
  huan_luyen_quan_ly?: HuanLuyenQuanLy | null;
  de_xuat_sop?: DeXuatSop[];
  do_tin_cay_tong_the?: number;
  trang_thai?: "cho_duyet" | "da_duyet" | "tu_choi";
}

export interface CopilotContext {
  store_id?: string;
  user_id: string;
  user_role: "chu_quan" | "quan_ly" | "nhan_vien";
  active_date: string;
  channel?: "web" | "telegram" | "zalo";
  recent_messages?: string[];
}

export interface CopilotMessage {
  message: string;
  context: CopilotContext;
}

export type ActionProposalStatus = "draft" | "ready_for_approval" | "amendment_ready" | "executing" | "executed" | "execution_failed" | "rejected" | "expired" | "stale_rejected";

export type CopilotIntent = "SCHEDULE_SOLVE" | "APPROVE_SHIFT_SWAP" | "GENERATE_DAILY_BRIEF" | "QUERY_SOP" | "ANALYZE_WASTE" | "CREATE_RULE_PROPOSAL" | "INVENTORY_RESTOCK_CHECK" | "SEND_MAIL" | "GET_MY_PROFILE" | "LIST_STAFF" | "QUERY_MENU" | "GET_INVENTORY" | "GET_SHIFT_SWAPS" | "GET_HANGING_TASKS" | "GET_HANDOVERS" | "PROPOSE_HANGING_TASK" | "PROPOSE_TASK_COMPLETE" | "PROPOSE_CONSUMPTION_RECORD" | "PROPOSE_MENU_UPDATE" | "PROPOSE_ORDER_TRANSITION" | "PROPOSE_PIN" | "GET_PAGE_STATUS" | "PROPOSE_PAGE_SYNC" | "OUT_OF_SCOPE";

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

export interface AIGenerationDraft {
  subject?: string | null;
  body: string;
}

export interface AIModelVersion {
  provider: string;
  model_id: string;
  model_revision?: string | null;
  temperature: number;
  tool_context_hash: string;
}

export interface AIGenerationRecord {
  id: string;
  store_id: string;
  channel: "gmail" | "facebook";
  conversation_id?: string | null;
  request_kind: "gmail_request" | "facebook_message" | "facebook_comment";
  external_event_hash?: string | null;
  draft: AIGenerationDraft;
  context_snapshot_hash: string;
  verified_fact_refs?: string[];
  missing_context?: boolean;
  agent_version: string;
  prompt_version: string;
  rule_version: string;
  rollout_bucket: "control" | "canary_10" | "canary_50" | "active_100";
  model: AIModelVersion;
  policy_action: FbPolicyAction;
  idempotency_key: string;
  created_at: string;
}

export interface AIFeedbackContent {
  subject?: string | null;
  body?: string | null;
}

export interface AIFeedbackEvent {
  id: string;
  store_id: string;
  generation_id: string;
  channel: "gmail" | "facebook";
  type: "manager_approve" | "manager_edit" | "manager_reject" | "customer_positive" | "customer_negative" | "customer_followup" | "send_success" | "send_failure" | "manual_rating";
  original?: AIFeedbackContent | null;
  final?: AIFeedbackContent | null;
  edited_fields?: Array<"subject" | "body">;
  materially_edited?: boolean;
  actor_user_id?: string | null;
  actor_role: "chu_quan" | "quan_ly" | "system" | "customer";
  send_status?: "not_applicable" | "sent" | "failed";
  failure_code?: string | null;
  idempotency_key: string;
  created_at: string;
}

export interface AIEvaluationScores {
  accuracy: number;
  safety: number;
  completeness?: number | null;
  tone?: number | null;
  naturalness?: number | null;
  personalization?: number | null;
  actionability?: number | null;
  policy_compliance?: number | null;
  intent_fit?: number | null;
  emotional_fit?: number | null;
  resolution_likelihood?: number | null;
}

export interface AIEvaluation {
  id: string;
  store_id: string;
  generation_id: string;
  channel: "gmail" | "facebook";
  scores: AIEvaluationScores;
  aggregate_score: number;
  passed: boolean;
  action: FbPolicyAction;
  hard_fail_flags?: string[];
  flags?: string[];
  threshold_version: string;
  calibration_version: string;
  sample_count: number;
  evaluation_window: string;
  evaluator: string;
  idempotency_key: string;
  created_at: string;
}

export interface AIRuleDefinition {
  text: string;
  intent_scope: string[];
  audience_scope: string[];
  priority: number;
}

export interface AIRuleRollout {
  mode?: "none" | "canary" | "full";
  percentage?: number;
  min_sample?: number;
  start_at?: string | null;
  end_at?: string | null;
}

export interface AIRuleProposal {
  id: string;
  store_id: string;
  channel: "gmail" | "facebook";
  rule_type: "style" | "prompt" | "playbook" | "safety";
  rule: AIRuleDefinition;
  evidence_count: number;
  evidence_ids: string[];
  confidence: number;
  status?: "pending" | "conflict_pending" | "approved" | "active" | "paused" | "rolled_back" | "rejected";
  version: number;
  rollback_target_version?: number | null;
  rollout?: AIRuleRollout;
  approved_by?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
}

export interface TableReservation {
  id: string;
  store_id?: string;
  psid?: string;
  customer_name: string;
  phone: string;
  booking_time: string;
  party_size: number;
  duration_minutes?: number;
  table_ids?: string[];
  status?: "held" | "confirmed" | "seated" | "completed" | "cancelled" | "no_show" | "needs_review";
  source?: "ai_auto" | "staff_manual";
  notes?: string;
  idempotency_key?: string;
  notified_nv_id?: string | null;
  notification_acked_at?: string | null;
  cancelled_by?: string | null;
  cancelled_reason?: string | null;
  created_at?: string;
  updated_at?: string;
}

