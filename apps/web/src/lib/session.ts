export type Role = "quan_ly" | "chu_quan" | "nhan_vien" | string;

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_token") ?? "";
}

export function getRole(): Role {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_role") ?? "";
}

export function getName(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_name") ?? "";
}

export function isManager(role = getRole()): boolean {
  return role === "quan_ly" || role === "chu_quan";
}

export function isChuQuan(role = getRole()): boolean {
  return role === "chu_quan";
}

export function canEdit(role = getRole()): boolean {
  return isManager(role);
}

const MANAGER_ONLY = new Set(["/roster", "/inbox"]);
const OWNER_ONLY = new Set(["/menu", "/nguoi", "/vet"]);

/** Client-side gate for navigation and hand-typed URLs. API remains authoritative. */
export function canAccess(role: Role, path: string): boolean {
  if (OWNER_ONLY.has(path)) return role === "chu_quan";
  if (MANAGER_ONLY.has(path)) return isManager(role);
  return Boolean(role);
}

export function clearSession(): void {
  sessionStorage.removeItem("nq_token");
  sessionStorage.removeItem("nq_role");
  sessionStorage.removeItem("nq_name");
  sessionStorage.removeItem("nq_nv");
}

export function roleLabel(role: string): string {
  if (role === "quan_ly") return "Quản lý";
  if (role === "chu_quan") return "Chủ quán";
  if (role === "nhan_vien") return "Nhân viên";
  return role || "Chưa đăng nhập";
}

export function lifeLabel(state: string): string {
  const map: Record<string, string> = {
    nhap: "Nháp",
    dang_giai: "Đang giải",
    cho_duyet: "Chờ duyệt",
    da_cong_bo: "Đã công bố",
    da_dong: "Đã đóng",
  };
  return map[state] ?? state;
}
