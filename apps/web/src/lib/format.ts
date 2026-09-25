const vnd = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

const dateVi = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const dateTimeVi = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function asDate(iso: unknown): Date | null {
  if (iso instanceof Date) return Number.isNaN(iso.getTime()) ? null : iso;
  if (typeof iso !== "string" && typeof iso !== "number") return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatVnd(n: unknown): string {
  const v = typeof n === "number" ? n : Number(n);
  if (!Number.isFinite(v)) return "—";
  return vnd.format(v);
}

export function formatDateVi(iso: unknown): string {
  const d = asDate(iso);
  return d ? dateVi.format(d) : "—";
}

export function formatDateTimeVi(iso: unknown): string {
  const d = asDate(iso);
  return d ? dateTimeVi.format(d) : "—";
}

export function formatDurationMs(ms: unknown): string {
  const n = typeof ms === "number" ? ms : Number(ms);
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n < 1000) return `${Math.round(n)} ms`;
  const s = n / 1000;
  if (s < 60) return `${s.toFixed(1)} giây`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return rem ? `${m} phút ${rem} giây` : `${m} phút`;
}

export function formatPercent(n: unknown, digits = 0): string {
  const v = typeof n === "number" ? n : Number(n);
  if (!Number.isFinite(v)) return "—";
  const pct = Math.abs(v) <= 1 ? v * 100 : v;
  return `${pct.toFixed(digits)}%`;
}
