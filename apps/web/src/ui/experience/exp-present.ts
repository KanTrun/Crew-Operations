/**
 * Nhãn tiếng Việt cho các mã enum của Grand AI Experience.
 *
 * Quy tắc dự án (design-guidelines §Disclosure): mọi mã trạng thái nội bộ phải
 * qua bảng nhãn — không in `draft`, `granted`, `rescue_case`… trực tiếp lên UI.
 * Module này là bản sao pattern của `lib/present.ts` (pick an toàn, fallback =
 * mã gốc chỉ khi lạ hoàn toàn — không bịa nhãn).
 */

export type Tone = "ok" | "warn" | "danger" | "default";

function pick(map: Record<string, string>, code: unknown, fallback: string): string {
  const key = typeof code === "string" ? code : "";
  return map[key] ?? fallback;
}

/** Mã trạng thái đề xuất (ExperienceProposalStatus). */
const PROPOSAL_LABELS: Record<string, string> = {
  draft: "Bản nháp",
  ready: "Sẵn sàng",
  confirmed: "Đã xác nhận",
  rejected: "Bị từ chối",
  expired: "Hết hạn",
};
export function proposalStatusLabel(code: unknown): string {
  return pick(PROPOSAL_LABELS, code, code === null || code === undefined ? "" : String(code));
}

/** Trạng thái đồng thuận ký ức. */
const CONSENT_LABELS: Record<string, string> = {
  required: "Cần đồng thuận",
  granted: "Đã đồng thuận",
  revoked: "Đã thu hồi",
  expired: "Đã hết hạn",
};
export function consentStatusLabel(code: unknown): string {
  return pick(CONSENT_LABELS, code, String(code));
}

/** Phạm vi hiển thị ký ức. */
const VISIBILITY_LABELS: Record<string, string> = {
  private: "Riêng tư",
  staff: "Nhóm nội bộ",
  manager: "Quản lý",
  public: "Công khai",
};
export function visibilityLabel(code: unknown): string {
  return pick(VISIBILITY_LABELS, code, String(code));
}

/** Trạng thái ký ức (status). */
const MEMORY_STATUS_LABELS: Record<string, string> = {
  draft: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  superseded: "Bị thay thế",
  deleted: "Đã xoá",
};
export function memoryStatusLabel(code: unknown): string {
  return pick(MEMORY_STATUS_LABELS, code, String(code));
}

/** Trạng thái ca cứu hộ. */
const RESCUE_STATUS_LABELS: Record<string, string> = {
  reported: "Đã báo vắng",
  resolving: "Đang xác định ca",
  candidates_ready: "Đã có danh sách người bù",
  proposed: "Đã đề xuất",
  invited: "Đã gửi lời mời",
  responded: "Đã nhận phản hồi",
  confirmed: "Đã xác nhận",
  expired: "Hết hạn",
  cancelled: "Đã huỷ",
};
export function rescueStatusLabel(code: unknown): string {
  return pick(RESCUE_STATUS_LABELS, code, String(code));
}

/** Loại sự kiện trên Living Map. */
const EVENT_TYPE_LABELS: Record<string, string> = {
  incident: "Sự cố",
  process: "Quy trình",
  voice_note: "Ghi chú thoại",
  praise: "Lời khen",
  operation_memory: "Ký ức vận hành",
  decision: "Quyết định",
  mode_change: "Chế độ",
  proposal_confirmed: "Đã duyệt đề xuất",
  proposal_rejected: "Từ chối đề xuất",
  anchor_status: "Trạng thái khu vực",
  rescue_case: "Cứu ca",
  signal: "Tín hiệu",
  mode_proposal: "Đề xuất chế độ",
  event: "Sự kiện",
};
export function eventTypeLabel(code: unknown): string {
  return pick(EVENT_TYPE_LABELS, code, String(code));
}

/** Trạng thái sự kiện công khai. */
const EVENT_STATUS_LABELS: Record<string, string> = {
  proposed: "Đang chờ duyệt",
  draft: "Bản nháp",
  ready: "Sẵn sàng",
  confirmed: "Đã xác nhận",
  candidates_ready: "Đang chờ chọn người",
  done: "Hoàn tất",
  closed: "Đã đóng",
};
export function eventStatusLabel(code: unknown): string {
  return pick(EVENT_STATUS_LABELS, code, String(code));
}

/** Loại mục tầm nhìn 15 phút. */
const HORIZON_KIND_LABELS: Record<string, string> = {
  event: "Sự kiện",
  signal: "Tín hiệu",
  handover: "Bàn giao",
  mode_proposal: "Đề xuất chế độ",
};
export function horizonKindLabel(code: unknown): string {
  return pick(HORIZON_KIND_LABELS, code, String(code));
}

/** Chế độ quán. */
const MODE_LABELS: Record<string, string> = {
  troi_mua: "Trời mưa",
  gio_cao_diem: "Giờ cao điểm",
  khach_doan: "Khách đoàn",
  thieu_nhan_su: "Thiếu nhân sự",
  quan_yen_tinh: "Quán yên tĩnh",
  dem_nhac: "Đêm nhạc",
};
export function modeLabel(code: unknown): string {
  return pick(MODE_LABELS, code, String(code));
}

/** Kết quả xác nhận proposal. */
export function confirmOutcomeLabel(ok: boolean): string {
  return ok ? "Đã xác nhận" : "Không xác nhận";
}

/** Reason code eligibility (Shift Rescue) → tiếng Việt. */
const ELIGIBILITY_REASON_LABELS: Record<string, string> = {
  C01: "Trùng giờ học (TKB)",
  C02: "Thiếu kỹ năng vị trí",
  C03: "Trùng ca cùng lúc",
  C04: "Chưa đủ giờ nghỉ tối thiểu",
  C05: "Vượt trần giờ tuần",
  C06: "Đang nghỉ phép đã duyệt",
  SKILL: "Thiếu kỹ năng",
  CAP: "Vượt trần giờ",
  SELF: "Không thể thay chính mình",
  thieu_ky_nang: "Thiếu kỹ năng vị trí",
  vuot_tran_gio: "Vượt trần giờ tuần",
  hard_constraints_ok: "Đạt mọi ràng buộc cứng",
};
export function eligibilityReasonLabel(code: unknown): string {
  const key = typeof code === "string" ? code.toUpperCase() : "";
  if (key in ELIGIBILITY_REASON_LABELS) return ELIGIBILITY_REASON_LABELS[key];
  return pick(ELIGIBILITY_REASON_LABELS, code, String(code));
}

/** Priority pass reason (dạng "fairness_delta=1.20") → tách nhãn gọn. */
export function passReasonLabel(text: string): string {
  if (text.startsWith("fairness_delta=")) return `Chênh lệch công bằng ${Number(text.split("=")[1]).toFixed(2)}`;
  if (text.startsWith("added_hours=")) return `Thêm ${text.split("=")[1]} giờ`;
  if (text.startsWith("policy_version=")) return `Chính sách ${text.split("=")[1]}`;
  return eligibilityReasonLabel(text);
}

/** Tên lựa chọn War Room từ option_id (vd opt_crisis_rain_scn → Mưa lớn). */
export function warOptionTitle(optionId: string, fallback: string): string {
  if (optionId.includes("crisis_rain")) return "Mưa lớn";
  if (optionId.includes("crisis_peak") || optionId.includes("demand")) return "Giờ cao điểm";
  if (optionId.includes("crisis_short") || optionId.includes("staff")) return "Thiếu nhân sự";
  if (optionId.includes("crisis_outage") || optionId.includes("equipment")) return "Thiết bị hỏng";
  if (optionId.includes("crisis_group") || optionId.includes("large")) return "Khách đoàn";
  return fallback;
}

/** Loại nguồn. */
const SOURCE_LABELS: Record<string, string> = {
  replay: "Fixture replay",
  user: "Người dùng",
  system: "Hệ thống",
  agent: "Trợ lý AI",
};
export function sourceLabel(code: unknown): string {
  return pick(SOURCE_LABELS, code, String(code));
}

/** Kênh dự phòng của AR-lite khi thiết bị không mở được camera. */
const AR_FALLBACK_LABELS: Record<string, string> = {
  map_or_qr_text: "mở bản đồ hoặc quét mã QR kèm chữ",
  none: "không cần dự phòng",
  text: "chỉ hiện chữ hướng dẫn",
  map: "chuyển sang bản đồ 2D",
};
export function arFallbackLabel(code: unknown): string {
  return pick(AR_FALLBACK_LABELS, code, String(code));
}

/** Loại khu vực trên Living Map. */
const ZONE_KIND_LABELS: Record<string, string> = {
  quay: "Quầy",
  phong_khach: "Khu khách",
  loi_vao: "Lối vào",
  kho: "Kho",
  ve_sinh: "Vệ sinh",
};
export function zoneKindLabel(code: unknown): string {
  return pick(ZONE_KIND_LABELS, code, String(code));
}

/** Mức chất lượng dữ liệu của snapshot. */
const DATA_LEVEL_LABELS: Record<string, string> = {
  info: "Thông tin",
  warn: "Cần lưu ý",
  error: "Thiếu dữ liệu",
  debug: "Kỹ thuật",
  ok: "Đầy đủ",
};
export function dataQualityLevelLabel(code: unknown): string {
  return pick(DATA_LEVEL_LABELS, code, String(code));
}

/** Mã chất lượng dữ liệu → câu người đọc được. */
const DATA_CODE_LABELS: Record<string, string> = {
  fixture_replay: "Đang chạy dữ liệu diễn tập",
  public_mode: "Bản chiếu khách — không kèm dữ liệu vận hành",
  stale_snapshot: "Ảnh trạng thái đã cũ",
  rate_limited: "Đã chạm trần truy vấn",
  missing_horizon: "Chưa có tầm nhìn 15 phút",
};
export function dataQualityLabel(code: unknown): string {
  return pick(DATA_CODE_LABELS, code, String(code));
}

/** Điểm của một khu vực trên Living Map (tải thấp/vừa/cao). */
export function zoneLoadLabel(load: unknown): string {
  const n = typeof load === "number" ? load : Number(load);
  if (!Number.isFinite(n)) return "Không rõ tải";
  const pct = Math.round(n * 100);
  if (n >= 0.7) return `Tải cao ${pct}%`;
  if (n >= 0.4) return `Tải vừa ${pct}%`;
  return `Tải nhẹ ${pct}%`;
}