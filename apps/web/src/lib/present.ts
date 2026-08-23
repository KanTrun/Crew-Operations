/**
 * Lớp trình bày — chốt kiểm duyệt hiển thị của apps/web.
 *
 * Ba việc, đều là ràng buộc từ `docs/design-guidelines.md`:
 *  1. Lỗi kỹ thuật → câu tiếng Việt người vận hành hiểu, kèm hành động kế tiếp.
 *     Không stack trace, không JSON lỗi, không mã HTTP, không tên biến.
 *  2. Mã trạng thái nội bộ (`cho_duyet`, `ag_msg`, `pin_ca`…) → nhãn tiếng Việt.
 *  3. Giá trị `null`/`undefined`/object → dấu gạch, tuyệt đối không "[object Object]".
 */
import { ApiError } from "./api";

const DASH = "—";

/** Ép mọi giá trị lạ về chuỗi an toàn cho UI. */
export function safeText(value: unknown, fallback = DASH): string {
  if (value == null) return fallback;
  if (typeof value === "string") return value.trim() === "" ? fallback : value;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : fallback;
  if (typeof value === "boolean") return value ? "có" : "không";
  return fallback;
}

/** Số thực an toàn — dùng cho số dư công bằng, số lượng tồn. */
export function safeNumber(value: unknown, digits = 1): string {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : DASH;
}

export type ErrorCopy = {
  /** Việc đang làm, viết tiếp được sau chữ "không": "đọc được bảng hôm nay". */
  doing: string;
  forbidden?: string;
  missing?: string;
  conflict?: string;
};

/**
 * Đổi lỗi bất kỳ thành một câu tiếng Việt + hành động kế tiếp.
 * Chỉ đọc `status`; không bao giờ đọc `message`, nên không có đường nào để
 * chuỗi kỹ thuật của máy chủ lọt ra UI.
 */
export function viError(err: unknown, copy: ErrorCopy): string {
  const status = err instanceof ApiError ? err.status : -1;
  if (status === 0) {
    return `Chưa nối được máy chủ quán nên không ${copy.doing}. Kiểm tra mạng rồi bấm tải lại.`;
  }
  if (status === 401) {
    return "Phiên làm việc đã hết. Đăng nhập lại rồi làm tiếp.";
  }
  if (status === 403) {
    return copy.forbidden ?? `Bạn không có quyền ${copy.doing}. Nhờ quản lý hoặc chủ quán làm bước này.`;
  }
  if (status === 404) {
    return (
      copy.missing ??
      `Không tìm thấy dữ liệu để ${copy.doing}. Tải lại trang; nếu vẫn trống thì nhắn quản lý kiểm tra dữ liệu quán.`
    );
  }
  if (status === 409) {
    return copy.conflict ?? "Dữ liệu vừa đổi ở nơi khác. Tải lại trang rồi làm lại từ đầu.";
  }
  if (status === 400 || status === 422) {
    return "Thông tin nhập chưa hợp lệ. Kiểm tra lại các ô rồi gửi lại.";
  }
  if (status === 429) {
    return "Quá nhiều lượt trong thời gian ngắn. Chờ một phút rồi thử lại.";
  }
  if (status >= 500) {
    return `Máy chủ quán đang lỗi nên không ${copy.doing}. Thử lại sau ít phút, nếu vẫn vậy báo quản lý.`;
  }
  return `Không ${copy.doing}. Tải lại trang rồi thử lại; nếu vẫn vậy báo quản lý.`;
}

/* ── Nhãn người, không lộ tên và không lộ mã thô ── */

/** `nv_03` → "Nhân viên 03". Không in mã nội bộ, không in tên thật. */
export function nvLabel(id?: string | null): string {
  const raw = safeText(id, "");
  if (!raw) return "Nhân viên trong quán";
  const num = raw.match(/(\d+)\s*$/);
  if (num) return `Nhân viên ${num[1]}`;
  if (raw === "quan_ly") return "Quản lý";
  if (raw === "chu_quan") return "Chủ quán";
  if (raw === "nhan_vien") return "Nhân viên";
  return "Nhân viên trong quán";
}

/** Người thực hiện trong sổ vết: vai trò hoặc nhân viên, không tên riêng. */
export function actorLabel(ai?: string | null): string {
  const raw = safeText(ai, "");
  if (!raw) return "Không rõ người thực hiện";
  if (raw === "quan_ly") return "Quản lý";
  if (raw === "chu_quan") return "Chủ quán";
  if (raw === "nhan_vien") return "Nhân viên";
  return nvLabel(raw);
}

/* ── Nhãn trạng thái ── */

function pick(map: Record<string, string>, code: unknown, fallback: string): string {
  const key = typeof code === "string" ? code : "";
  return map[key] ?? fallback;
}

const INBOX: Record<string, string> = {
  cho_duyet: "Chờ người duyệt",
  duyet: "Đã duyệt",
  tu_choi: "Đã từ chối",
  moi: "Mới vào hộp thư",
};

export function inboxLabel(code: unknown): string {
  return pick(INBOX, code, "Chưa rõ trạng thái");
}

export function inboxTone(code: unknown): "warn" | "ok" | "danger" | "default" {
  if (code === "cho_duyet" || code === "moi") return "warn";
  if (code === "duyet") return "ok";
  if (code === "tu_choi") return "danger";
  return "default";
}

const AGENT: Record<string, string> = {
  ag_msg: "Tin nhắn trong ca",
  ag_handover: "Bàn giao ca",
  ag_rule: "Đề xuất luật",
  ag_waste: "Ghi chú hao phí",
  ag_sop: "Câu hỏi SOP",
};

export function agentLabel(code: unknown): string {
  return pick(AGENT, code, "Nguồn trong quán");
}

const LUAT: Record<string, string> = {
  de_xuat: "Mới đề xuất",
  qua_vf_rule: "Qua vòng kiểm",
  loai: "Bị loại ở vòng kiểm",
  du_tap_su: "Đủ lượt tập sự",
  truot_tap_su: "Chưa đủ lượt tập sự",
  tu_choi: "Quản lý từ chối",
  hieu_luc: "Đang hiệu lực",
  tu_tat: "Tự tắt vì ít dùng",
};

export function luatLabel(code: unknown): string {
  return pick(LUAT, code, "Chưa rõ trạng thái");
}

export function luatTone(code: unknown): "warn" | "ok" | "danger" | "default" {
  if (code === "hieu_luc") return "ok";
  if (code === "loai" || code === "tu_choi") return "danger";
  if (code === "de_xuat" || code === "truot_tap_su") return "warn";
  return "default";
}

const GHI_NHAN: Record<string, string> = {
  pin_ca: "Ghim người vào ca",
  nha_ca: "Nhả ca",
  nhan_ca: "Nhận ca",
  sua_lich: "Sửa lịch tuần",
};

export function ghiNhanLabel(code: unknown): string {
  return pick(GHI_NHAN, code, "Lần sửa trong quán");
}

const HANH_VI: Record<string, string> = {
  lifecycle: "Chuyển trạng thái lịch tuần",
  inbox: "Quyết định hộp thư ràng buộc",
  tieu_thu: "Ghi sổ tiêu thụ",
  cam_nang_8_buoc: "Chạy 8 bước cẩm nang",
  swap: "Mở lệnh đổi ca",
  pin_ca: "Ghim người vào ca",
};

export function hanhViLabel(code: unknown): string {
  return pick(HANH_VI, code, "Thao tác trong quán");
}

const SWAP: Record<string, string> = {
  cho_3_nhanh: "Chờ cả ba nhánh đồng ý",
  dong_y: "Ba nhánh đã đồng ý",
  tu_choi: "Có nhánh từ chối",
  huy: "Đã hủy",
};

export function swapLabel(code: unknown): string {
  return pick(SWAP, code, "Chưa rõ trạng thái");
}

const KHUNG: Record<string, string> = {
  sang: "Ca sáng",
  chieu: "Ca chiều",
  toi: "Ca tối",
};

export function khungLabel(code: unknown): string {
  return pick(KHUNG, code, "");
}

const LOAI_BUOC: Record<string, string> = {
  photo: "Bước cần ảnh minh chứng",
  text: "Bước cần nhập số liệu",
  nhap: "Bước cần nhập số liệu",
  check: "Bước xác nhận bằng tay",
  doc: "Bước đọc và làm theo",
};

export function loaiBuocLabel(code: unknown): string {
  return pick(LOAI_BUOC, code, "Bước trong phiếu");
}

/* ── Thời gian ── */

/** ISO → "23/08 14:05". Chuỗi rác trả về gạch thay vì "Invalid Date". */
export function formatLuc(value?: string | null): string {
  const raw = safeText(value, "");
  if (!raw) return DASH;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return DASH;
  const p2 = (n: number) => String(n).padStart(2, "0");
  return `${p2(d.getDate())}/${p2(d.getMonth() + 1)} ${p2(d.getHours())}:${p2(d.getMinutes())}`;
}

/** Ngày ISO `2026-08-23` → "23/08". Không đụng tới chuỗi lạ. */
export function formatNgay(value?: string | null): string {
  const raw = safeText(value, "");
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}/${m[2]}` : raw || DASH;
}

/**
 * Che mã một lần. Mã điểm danh là bí mật dùng-một-lần: in nguyên lên màn hình
 * là để lộ credential (`docs/design-guidelines.md` — Disclosure rules).
 */
export function maskCode(code: string): string {
  const raw = safeText(code, "");
  if (!raw) return DASH;
  if (raw.length <= 4) return "••••";
  return `•••• •••• ${raw.slice(-4)}`;
}
