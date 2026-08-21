export type NhanVien = Record<string, unknown>;
export type Ca = Record<string, unknown>;
export type LichTuan = Record<string, unknown>;
export type PhieuMau = Record<string, unknown>;
export type RangBuocTrichXuat = Record<string, unknown>;

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchContracts(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API}/api/v1/contracts`, { cache: "no-store" });
  if (!res.ok) throw new Error("contracts_failed");
  return res.json();
}
