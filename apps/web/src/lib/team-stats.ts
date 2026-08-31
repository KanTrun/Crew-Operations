import { roleLabel } from "./session";

export type TeamUser = {
  username: string;
  role: string;
  nv_id: string;
  display_name: string;
};

export type RoleCounts = {
  all: number;
  chu_quan: number;
  quan_ly: number;
  nhan_vien: number;
};

export type RoleSlice = {
  role: string;
  label: string;
  n: number;
  color: string;
};

export type TeamInsight = {
  severity: "ok" | "warn" | "info";
  message: string;
};

const ROLE_COLORS: Record<string, string> = {
  chu_quan: "#6f9b7a",
  quan_ly: "#c4a574",
  nhan_vien: "#8b7355",
};

const ROLE_ORDER = ["chu_quan", "quan_ly", "nhan_vien"] as const;

export function countRoles(items: TeamUser[]): RoleCounts {
  const c: RoleCounts = { all: items.length, chu_quan: 0, quan_ly: 0, nhan_vien: 0 };
  for (const u of items) {
    if (u.role === "chu_quan") c.chu_quan += 1;
    else if (u.role === "quan_ly") c.quan_ly += 1;
    else if (u.role === "nhan_vien") c.nhan_vien += 1;
  }
  return c;
}

export function roleBreakdown(counts: RoleCounts): RoleSlice[] {
  return ROLE_ORDER.filter((role) => counts[role] > 0).map((role) => ({
    role,
    label: roleLabel(role),
    n: counts[role],
    color: ROLE_COLORS[role] ?? "#5c7a8a",
  }));
}

export function computeTeamInsight(counts: RoleCounts): TeamInsight {
  if (counts.quan_ly === 0) {
    return {
      severity: "warn",
      message: "Chưa có quản lý ca — hộp thư và lịch tuần không ai duyệt khi bạn vắng.",
    };
  }
  if (counts.all <= 1) {
    return {
      severity: "info",
      message: "Chỉ có chủ quán — nhân viên đăng ký sẽ xuất hiện ở đây để bạn nâng vai.",
    };
  }
  if (counts.quan_ly === 1 && counts.nhan_vien > 0) {
    return {
      severity: "info",
      message: `1 quản lý ca phụ trách ${counts.nhan_vien} nhân viên — cân nhắc thêm QL nếu ca đông.`,
    };
  }
  return {
    severity: "ok",
    message: `${counts.quan_ly} quản lý ca cho ${counts.nhan_vien} nhân viên — cơ cấu ổn định.`,
  };
}

export function userInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export function technicalUserLines(users: TeamUser[]): string[] {
  return users.map((u) => `${u.display_name} (@${u.username}) — mã NV: ${u.nv_id}`);
}
