import { khungLabel } from "./present";

export type KhungGio = Record<string, { bat_dau: string; ket_thuc: string }>;

export type RosterShift = {
  id: string;
  thu?: string;
  khung?: string;
  bat_dau?: string;
  ket_thuc?: string;
  vi_tri?: string;
  so_nguoi_toi_thieu?: number;
};

const KHUNG_ORDER = ["sang", "chieu", "toi"] as const;

export function khungOrder(khung: string): number {
  const i = KHUNG_ORDER.indexOf(khung as (typeof KHUNG_ORDER)[number]);
  return i >= 0 ? i : 9;
}

/** Nhãn hàng: "Ca sáng · 06:00 – 11:00" từ data thật, không hardcode. */
export function shiftRowLabel(shift: RosterShift | undefined, khung: string, template?: KhungGio): string {
  const name = khungLabel(khung) || khung;
  const bat = shift?.bat_dau ?? template?.[khung]?.bat_dau;
  const ket = shift?.ket_thuc ?? template?.[khung]?.ket_thuc;
  if (bat && ket) return `${name} · ${bat} – ${ket}`;
  return name;
}

export function shiftTimeRange(shift: RosterShift, template?: KhungGio): string {
  const khung = shift.khung ?? "";
  const bat = shift.bat_dau ?? template?.[khung]?.bat_dau;
  const ket = shift.ket_thuc ?? template?.[khung]?.ket_thuc;
  if (bat && ket) return `${bat} – ${ket}`;
  return "";
}

/**
 * Chữ viết tắt cho avatar ô lịch tuần.
 *
 * Vì sao không in tên đầy đủ: ô lịch chỉ rộng ~110px, mà một ca bar có thể có
 * 4–6 người. In tên đầy đủ thì CSS phải cắt bằng `-webkit-line-clamp`, và tên
 * người thứ ba trở đi biến mất sau dấu "…" — người xếp lịch không biết ca đó
 * còn ai. Viết tắt giữ được ĐỦ SỐ NGƯỜI trong cùng diện tích; tên đầy đủ nằm ở
 * tooltip và ở bảng chi tiết ngày.
 *
 * Tên tiếng Việt 2–4 từ: lấy chữ đầu của từ đầu + chữ đầu của từ cuối
 * ("Nguyễn Thị Lan" → "NL"). Tên một từ ("Hân") → hai ký tự đầu ("HÂ"). Giữ
 * dấu ở chữ cái đầu vì bỏ dấu làm nhiều tên trùng nhau.
 */
export function initialsOf(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0] ?? "";
  if (words.length === 1) return first.slice(0, 2).toUpperCase();
  const last = words[words.length - 1] ?? "";
  return ((first[0] ?? "") + (last[0] ?? "")).toUpperCase();
}

export function rosterCellSummary(count: number, viTriLabel: string, understaffed?: boolean): {
  countLabel: string;
  roleLabel: string;
  tone: "ok" | "warn" | "empty";
} {
  if (count === 0) {
    // Ô chưa xếp ai là lỗi vận hành, không phải "0 người" trung tính: ca trống
    // nghĩa là quán mở cửa mà không có ai. Tông `empty` tách khỏi `warn` để
    // "thiếu 1 người" và "trống ca" không đọc ra như nhau.
    return { countLabel: "Trống ca", roleLabel: viTriLabel, tone: "empty" };
  }
  return {
    countLabel: `${count} người`,
    roleLabel: viTriLabel,
    tone: understaffed ? "warn" : "ok",
  };
}
