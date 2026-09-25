/** Nhãn tiếng Việt cho khóa API — dùng với DataList, không in snake_case thô. */

export const FIELD_LABELS: Record<string, string> = {
  csat_score: "Điểm hài lòng",
  sentiment_breakdown: "Phân bố cảm xúc",
  scenario_id: "Mã kịch bản",
  ket_qua: "Kết quả",
  loai: "Loại",
  criteria: "Điều kiện",
  action: "Hành động",
  payload: "Nội dung",
  agent_lich: "Trợ lý lịch",
  agent_name: "Trợ lý",
  trang_thai: "Trạng thái",
  created_at: "Tạo lúc",
  updated_at: "Cập nhật",
  nv_id: "Nhân viên",
  ca_id: "Ca",
  khung: "Khung giờ",
  thu: "Thứ",
  bat_dau: "Bắt đầu",
  ket_thuc: "Kết thúc",
  vi_tri: "Vị trí",
  so_luong: "Số lượng",
  don_gia: "Đơn giá",
  thanh_tien: "Thành tiền",
  ghi_chu: "Ghi chú",
  ly_do: "Lý do",
  muc_do: "Mức độ",
  do_tin_cay: "Độ tin cậy",
  nguon: "Nguồn",
  tieu_de: "Tiêu đề",
  noi_dung: "Nội dung",
  email_from: "Người gửi",
  email_to: "Người nhận",
  subject: "Tiêu đề thư",
  label: "Nhãn",
  filter: "Bộ lọc",
  from: "Từ",
  to: "Đến",
  has_attachment: "Có tệp đính kèm",
  mark_as_read: "Đánh dấu đã đọc",
  apply_label: "Gắn nhãn",
  forward_to: "Chuyển tới",
  risk_level: "Mức rủi ro",
  impact: "Tác động",
  mitigation: "Giảm thiểu",
  schedule_run_id: "Lần chạy lịch",
  workflow: "Quy trình",
  score: "Điểm",
  rank: "Thứ hạng",
  count: "Số lượng",
  total: "Tổng",
  error: "Lỗi",
  message: "Thông báo",
  status: "Trạng thái",
  type: "Loại",
  id: "Mã",
  name: "Tên",
  ten: "Tên",
  phone: "Điện thoại",
  email: "Email",
};

export function fieldLabel(key: string): string {
  if (!key) return "—";
  const hit = FIELD_LABELS[key] ?? FIELD_LABELS[key.toLowerCase()];
  if (hit) return hit;
  return key
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());
}

export function formatFieldValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "—";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    if (value.every((v) => typeof v !== "object" || v == null)) {
      return value.map((v) => String(v)).join(", ");
    }
    return `${value.length} mục`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value as object);
    return keys.length ? `${keys.length} trường` : "—";
  }
  return String(value);
}
