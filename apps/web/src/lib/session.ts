export type Role = "quan_ly" | "chu_quan" | "nhan_vien" | string;

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_token") || localStorage.getItem("nq_token") || "";
}

export function getRole(): Role {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_role") || localStorage.getItem("nq_role") || "";
}

export function getName(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_name") || localStorage.getItem("nq_name") || "";
}

export function setSession(token: string, role: string, name: string, nvId: string): void {
  try {
    sessionStorage.setItem("nq_token", token);
    sessionStorage.setItem("nq_role", role);
    sessionStorage.setItem("nq_name", name);
    sessionStorage.setItem("nq_nv", nvId);
  } catch {}
  try {
    localStorage.setItem("nq_token", token);
    localStorage.setItem("nq_role", role);
    localStorage.setItem("nq_name", name);
    localStorage.setItem("nq_nv", nvId);
  } catch {}
}

export function getNvId(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("nq_nv") || localStorage.getItem("nq_nv") || "";
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

const STAFF_ACCESS = new Set([
  "/hom-nay",
  "/cuoc-hop",
  "/quay",
  "/pha",
  "/phieu",
  "/toi",
  "/treo",
  "/doi-ca",
  "/handover",
  "/hao-phi",
  "/tieu-thu",
  "/cong-bang",
  "/sop",
  "/tkb",
  "/qr",
  "/cam-nang",
  "/copilot",
  "/them",
  "/contracts",
]);
const MANAGER_ONLY = new Set(["/roster", "/inbox", "/page-quan", "/ai-learning"]);
const OWNER_ONLY = new Set(["/menu", "/nguoi", "/vet"]);

/** Client-side gate for navigation and hand-typed URLs. API remains authoritative. */
export function canAccess(role: Role, path: string): boolean {
  if (OWNER_ONLY.has(path)) return role === "chu_quan";
  if (MANAGER_ONLY.has(path)) return isManager(role);
  return STAFF_ACCESS.has(path) && Boolean(role);
}

export function clearSession(): void {
  try {
    sessionStorage.removeItem("nq_token");
    sessionStorage.removeItem("nq_role");
    sessionStorage.removeItem("nq_name");
    sessionStorage.removeItem("nq_nv");
  } catch {}
  try {
    localStorage.removeItem("nq_token");
    localStorage.removeItem("nq_role");
    localStorage.removeItem("nq_name");
    localStorage.removeItem("nq_nv");
  } catch {}
}

export function roleLabel(role: string): string {
  if (role === "quan_ly") return "Quản lý";
  if (role === "chu_quan") return "Chủ quán";
  if (role === "nhan_vien") return "Nhân viên";
  return role || "Chưa đăng nhập";
}

export function lifeLabel(state: string): string {
  const map: Record<string, string> = {
    may_sinh: "Tự sinh — chờ rà soát",
    nhap: "Nháp",
    dang_giai: "Đang giải",
    cho_duyet: "Chờ duyệt",
    da_duyet: "Đã duyệt",
    da_cong_bo: "Đã công bố",
    da_dong: "Đã đóng",
  };
  return map[state] ?? state.replace(/_/g, " ");
}
