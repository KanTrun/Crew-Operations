import { khungLabel } from "./present";

export type KhungGio = Record<string, { bat_dau: string; ket_thuc: string }>;

export type RosterShift = {
  id: string;
  thu?: string;
  khung?: string;
  bat_dau?: string;
  ket_thuc?: string;
  vi_tri?: string;
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

export function rosterCellSummary(count: number, viTriLabel: string, understaffed?: boolean): {
  countLabel: string;
  roleLabel: string;
  tone: "ok" | "warn" | "empty";
} {
  if (count === 0) {
    return { countLabel: "Thiếu người", roleLabel: viTriLabel, tone: "empty" };
  }
  return {
    countLabel: `${count} NV`,
    roleLabel: viTriLabel,
    tone: understaffed ? "warn" : "ok",
  };
}
