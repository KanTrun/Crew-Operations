import { lifeLabel } from "./session";

/** Nhãn human-facing — không dump mã nội bộ lên hero. */
export function lifeLabelPublic(state: string): string {
  const map: Record<string, string> = {
    nhap: "Lịch nháp",
    dang_giai: "Đang xếp lịch",
    cho_duyet: "Chờ duyệt",
    da_cong_bo: "Lịch đã công bố",
    da_dong: "Tuần đã đóng",
  };
  return map[state] ?? lifeLabel(state);
}

export function todayHeroLine(treo: number, lifeState?: string): string {
  const life = lifeLabelPublic(lifeState ?? "");
  return `${life} · ${treo} việc treo`;
}

export function todayMetaLine(ngay: string, nguon?: string): string {
  const src = nguon === "quan" ? "nguồn quán" : nguon ? `nguồn ${nguon}` : "nguồn quán";
  return `Ngày ${ngay} · ${src}`;
}

export function todayTechnicalDetail(lich: {
  trang_thai?: string;
  solver?: { status?: string };
}): string[] {
  const lines: string[] = [];
  if (lich.trang_thai) lines.push(`Trạng thái lịch: ${lifeLabel(lich.trang_thai)}`);
  if (lich.solver?.status) lines.push(`Solver: ${lich.solver.status}`);
  return lines;
}
