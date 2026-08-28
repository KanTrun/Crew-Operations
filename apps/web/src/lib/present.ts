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

/* ── Nhãn người ──
   `nvLabel(id)` cố ý ẩn tên riêng (công bằng / sổ vết).
   Lưới lịch và chọn người dùng `ten` từ API; `nvTenHienThi` chuẩn hóa chuỗi đó. */

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

/** Tên trên lưới ca: ưu tiên `ten` từ máy chủ; bỏ dạng placeholder "Nhan Vien 01". */
export function nvTenHienThi(ten: unknown, id?: string | null): string {
  const name = safeText(ten, "");
  if (name && !/^nhan\s*vien\s*\d+$/i.test(name.replace(/\s+/g, " ").trim())) {
    return name;
  }
  return nvLabel(id);
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

/* ── Vị trí / chức vụ ca ── */

const VI_TRI: Record<string, string> = {
  thu_ngan: "Thu ngân",
  pha_che: "Pha chế",
  phuc_vu: "Phục vụ",
  kho: "Kho",
  quan_ly_ca: "Quản lý ca",
  da_nang: "Đa năng",
};

export function viTriLabel(code: unknown): string {
  const raw = safeText(code, "");
  if (!raw) return "Chưa ghi vị trí";
  return pick(VI_TRI, raw, raw.includes("_") ? raw.replace(/_/g, " ") : raw);
}


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
  ag_tkb: "Thời khoá biểu nhân viên",
};

export function agentLabel(code: unknown): string {
  return pick(AGENT, code, "Nguồn trong quán");
}

const LUAT: Record<string, string> = {
  de_xuat: "Mới đề xuất",
  qua_vf_rule: "Qua vòng kiểm",
  loai: "Bị loại ở vòng kiểm",
  du_tap_su: "Đủ lượt tập sự",
  cho_chu_quan: "Chờ chủ quán chốt",
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
  if (code === "de_xuat" || code === "truot_tap_su" || code === "cho_chu_quan") return "warn";
  return "default";
}

/* ── Việc treo ──
   Ba trạng thái từ máy chủ (`xong` · `dang_cho` · `qua_han`) là mã nội bộ, phải
   đi qua bảng nhãn như mọi mã khác. Việc treo quá hạn tô đỏ vì đó là việc quán
   đang nợ chính mình. */

const TREO: Record<string, string> = {
  xong: "Đã xong",
  dang_cho: "Đang chờ làm",
  qua_han: "Quá hạn",
  moi: "Mới ghi",
};

export function treoLabel(code: unknown): string {
  return pick(TREO, code, "Chưa rõ trạng thái");
}

export function treoTone(code: unknown): "warn" | "ok" | "danger" | "default" {
  if (code === "xong") return "ok";
  if (code === "qua_han") return "danger";
  if (code === "dang_cho") return "warn";
  return "default";
}

/** Thứ tự đọc: việc quá hạn trước, việc đang chờ, việc đã xong sau cùng. */
export const TREO_THU_TU: readonly string[] = ["qua_han", "dang_cho", "xong"];

/* ── Loại luật trong cẩm nang ── */

const LOAI_LUAT: Record<string, string> = {
  nhu_cau_ca: "Nhu cầu người cho một ca",
  nguong_ton: "Ngưỡng tồn kho",
  buoc_phieu: "Bước bắt buộc trong phiếu",
  ghep_ky_nang: "Ghép kỹ năng vào ca",
  hao_hut: "Nguyên nhân hao hụt",
  nguyen_nhan_hao_hut: "Nguyên nhân hao hụt",
};

export function loaiLuatLabel(code: unknown): string {
  return pick(LOAI_LUAT, code, "Loại luật khác");
}

/**
 * Lý do vòng kiểm loại một luật, nói bằng tiếng Việt.
 *
 * Máy chủ trả mã như `luat_ve_nguoi` hoặc `truong_khong_ton_tai:['ten_nhan_vien']`.
 * In mã thô lên UI là vi phạm mục Disclosure rules, nên ở đây chỉ đọc phần
 * trước dấu hai chấm rồi trả về câu giải thích; phần trong ngoặc (tên trường
 * kỹ thuật) bị bỏ hẳn.
 */
export function vfRuleLyDo(code: unknown): string {
  const raw = safeText(code, "");
  if (!raw) return "Vòng kiểm không ghi lý do.";
  const head = raw.split(":")[0];
  if (head === "dat") return "Luật này qua được vòng kiểm.";
  if (head === "luat_ve_nguoi") {
    return "Vòng kiểm loại vì luật nói về một người cụ thể. Cẩm nang chỉ nhận luật về việc, không nhận luật về người.";
  }
  if (head === "truong_khong_ton_tai") {
    return "Vòng kiểm loại vì luật dựa vào một thông tin quán không có trong hồ sơ ca. Viết lại điều kiện theo thứ, khung giờ hoặc ngưỡng tồn.";
  }
  if (head === "thieu_bang_chung") {
    return "Vòng kiểm loại vì chưa đủ lần sửa thật làm bằng chứng. Ghi thêm vài lần sửa rồi đề xuất lại.";
  }
  if (head === "trung_luat") {
    return "Vòng kiểm loại vì quán đã có một luật nói cùng một việc.";
  }
  return "Vòng kiểm loại luật này. Nhờ quản lý xem lại cách diễn đạt điều kiện.";
}

/* ── Hao phí ── */

const NGUYEN_NHAN: Record<string, string> = {
  dem_sai_dau_ca: "Đếm sai đầu ca",
  roi_do: "Rơi đổ khi làm",
  quen_tat_may: "Quên tắt máy",
  khach_doi_mon: "Khách đổi món",
  het_han: "Hết hạn dùng",
  "pha sai": "Pha sai phải bỏ",
  pha_sai: "Pha sai phải bỏ",
};

export function nguyenNhanLabel(code: unknown): string {
  return pick(NGUYEN_NHAN, code, "Nguyên nhân khác");
}

const MAT_HANG: Record<string, string> = {
  sua_tuoi: "sữa tươi",
  ca_phe_hat: "cà phê hạt",
  tra: "trà",
  duong: "đường",
  ly_nhua: "ly nhựa",
  ong_hut: "ống hút",
  banh: "bánh",
  da: "đá",
};

/** `sua_tuoi` → "sữa tươi". Tên đã là tiếng Việt thì giữ nguyên. */
export function matHangLabel(code: unknown): string {
  const raw = safeText(code, "");
  if (!raw) return "Mặt hàng chưa ghi tên";
  return MAT_HANG[raw] ?? raw;
}

const THU: Record<string, string> = {
  T2: "Thứ Hai",
  T3: "Thứ Ba",
  T4: "Thứ Tư",
  T5: "Thứ Năm",
  T6: "Thứ Sáu",
  T7: "Thứ Bảy",
  CN: "Chủ nhật",
};

export function thuLabel(code: unknown): string {
  return pick(THU, code, "Chưa rõ thứ");
}

/** Thứ tự tuần để nhóm hiển thị không nhảy theo thứ tự máy chủ trả về. */
export const THU_THU_TU: readonly string[] = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

/* ── Mẫu phiếu ── */

const MAU_PHIEU: Record<string, string> = {
  mo_quan: "Mở quán",
  dong_quan: "Đóng quán",
  ban_giao_ca: "Bàn giao ca",
};

export function mauPhieuLabel(code: unknown): string {
  return pick(MAU_PHIEU, code, "Phiếu ca");
}

/** Phiếu gắn vào lúc nào trong ngày — nói bằng lời, không dùng mã `ca_dau_ngay`. */
const GAN_VOI: Record<string, string> = {
  ca_dau_ngay: "Chạy ở ca đầu ngày, trước khi mở cửa cho khách",
  ca_cuoi_ngay: "Chạy ở ca cuối ngày, trước khi khoá cửa",
  giao_ca: "Chạy lúc giao ca, khi người ca trước rời quầy",
};

export function ganVoiLabel(code: unknown): string {
  return pick(GAN_VOI, code, "Chạy trong ca khi cần");
}

/** Điều kiện mở phiếu. Mã `nhan_vien_da_diem_danh` không được ra UI. */
const MO_KHI: Record<string, string> = {
  nhan_vien_da_diem_danh: "mở được sau khi bạn điểm danh",
  ca_ket_thuc: "mở được khi ca sắp kết thúc",
};

export function moKhiLabel(code: unknown): string {
  return pick(MO_KHI, code, "mở được trong ca");
}

/* ── Đăng ký tài khoản ──
   Máy chủ trả 409 với `detail` là một trong bốn mã. Mã thô không được ra UI:
   mỗi mã đổi thành một câu chỉ đúng ô cần sửa. */

export type ODangKy = "username" | "password" | "display_name" | "chung";

const DANG_KY: Record<string, { o: ODangKy; cau: string }> = {
  ten_khong_hop_le: {
    o: "username",
    cau: "Tên đăng nhập chỉ nhận chữ thường không dấu, số và dấu gạch dưới, dài 3–24 ký tự. Sửa lại ô tên đăng nhập.",
  },
  mat_khau_qua_ngan: {
    o: "password",
    cau: "Mật khẩu ngắn quá. Đặt từ 8 ký tự trở lên rồi gửi lại.",
  },
  ten_da_ton_tai: {
    o: "username",
    cau: "Tên đăng nhập này quán đã có người dùng. Chọn một tên khác, ví dụ thêm số ở cuối.",
  },
  thieu_ten_hien_thi: {
    o: "display_name",
    cau: "Tên hiển thị cần 2–60 ký tự để đồng nghiệp nhận ra bạn trên lịch ca.",
  },
};

/**
 * Đổi `detail` của lỗi 409 thành ô cần sửa + câu tiếng Việt.
 * Mã lạ cũng không lọt ra ngoài: rơi vào nhánh "chung" với câu chung.
 */
export function dangKyLoi(detail: unknown): { o: ODangKy; cau: string } {
  const raw = safeText(detail, "");
  return (
    DANG_KY[raw] ?? {
      o: "chung",
      cau: "Thông tin đăng ký chưa hợp lệ. Kiểm tra lại ba ô rồi gửi lại.",
    }
  );
}

/* ── Trích dẫn nguồn của câu trả lời SOP ──
   Máy chủ trả `phieu:<mã bước>` hoặc `luat:<mã luật>`. Mã là khoá để tra tên
   thật, KHÔNG phải thứ để in: trang /sop tra bảng mẫu phiếu và cẩm nang rồi in
   tên bước / câu luật. Không tra được thì in loại nguồn, vẫn không in mã. */

export type TrichDan = { loai: "phieu" | "luat" | "khac"; ma: string; nguon: string };

export function trichDanTach(raw: unknown): TrichDan {
  const s = safeText(raw, "");
  const i = s.indexOf(":");
  const dau = i >= 0 ? s.slice(0, i) : "";
  const ma = i >= 0 ? s.slice(i + 1) : "";
  if (dau === "phieu") return { loai: "phieu", ma, nguon: "Mẫu phiếu" };
  if (dau === "luat") return { loai: "luat", ma, nguon: "Cẩm nang" };
  return { loai: "khac", ma: "", nguon: "Nguồn quán" };
}

/* ── Ý định tin nhắn trong ca (AG-MSG) ──
   Sáu ý định máy chủ nhận ra từ câu người nhắn. Chip ý định cho người duyệt
   biết đây là loại việc gì trước khi đọc hết tóm tắt. */

const Y_DINH: Record<string, string> = {
  xin_nghi: "Xin nghỉ ca",
  nhan_ca: "Nhận ca",
  doi_ca: "Đổi ca",
  bao_tre: "Báo đến trễ",
  cap_nhat_tkb: "Cập nhật thời khoá biểu",
  khac: "Việc khác trong ca",
};

export function yDinhLabel(code: unknown): string {
  return pick(Y_DINH, code, "Chưa rõ ý định");
}

const KENH: Record<string, string> = {
  zalo: "Zalo",
  telegram: "Telegram",
  facebook: "Facebook",
  console: "Máy chủ",
  quan: "Trong quán",
  page_quan: "Page quán",
};

export function kenhLabel(code: unknown): string {
  return pick(KENH, code, "Kênh khác");
}

/* ── Loại ràng buộc kèm theo một mục hộp thư ── */

const RANG_BUOC: Record<string, string> = {
  khong_xep: "Không xếp vào ca này",
  co_the_xep: "Có thể xếp thêm",
  buoc_them: "Thêm bước vào phiếu",
  nguong_ton: "Ngưỡng tồn kho",
  nhu_cau_ca: "Nhu cầu người cho ca",
  doi_ca: "Đổi ca giữa hai người",
  bao_tre: "Đến trễ, cần bù người",
};

export function rangBuocLabel(code: unknown): string {
  return pick(RANG_BUOC, code, "Ràng buộc khác");
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
