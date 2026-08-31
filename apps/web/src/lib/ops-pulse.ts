/** Mô hình “nhịp AI” — map dữ liệu ops + solver → insight + hành động ưu tiên. */

export type OpsPulseInput = {
  treo: number;
  tonWarn: number;
  inboxCho: number;
  lichState?: string;
  solverStatus?: string;
  role: "chu_quan" | "quan_ly" | "nhan_vien";
};

export type OpsPulseSeverity = "ok" | "warn" | "critical";

export type OpsPulseModel = {
  pressure: number;
  aiActive: boolean;
  aiLabel: string;
  insight: string;
  href: string;
  cta: string;
  ariaLabel: string;
  severity: OpsPulseSeverity;
  particleCount: number;
  highlightKpi: "treo" | "ton" | "inbox" | "ai" | "ok";
};

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}

export function computeOpsPulse(input: OpsPulseInput): OpsPulseModel {
  const aiActive = input.lichState === "dang_giai";
  const treoNorm = clamp01(input.treo / 25);
  const tonNorm = clamp01(input.tonWarn / 5);
  const inboxNorm = input.role !== "nhan_vien" ? clamp01(input.inboxCho / 10) : 0;
  const pressure = clamp01(treoNorm * 0.55 + tonNorm * 0.3 + inboxNorm * 0.15 + (aiActive ? 0.25 : 0));

  let severity: OpsPulseSeverity = "ok";
  if (input.treo >= 15 || input.tonWarn >= 3) severity = "critical";
  else if (input.treo > 0 || input.tonWarn > 0 || input.inboxCho > 0 || aiActive) severity = "warn";

  const aiLabel = aiActive
    ? input.solverStatus
      ? `AI đang xếp lịch (${input.solverStatus})`
      : "AI đang xếp lịch (CP-SAT)"
    : "AI rảnh — chờ lệnh";

  if (aiActive) {
    return {
      pressure,
      aiActive: true,
      aiLabel,
      insight: "Bộ giải CP-SAT đang tối ưu lịch tuần. Kiểm tra kết quả trước khi công bố.",
      href: "/roster",
      cta: "Mở lịch tuần",
      ariaLabel: `AI đang xếp lịch. ${input.treo} việc treo. Bấm để mở lịch tuần.`,
      severity: "warn",
      particleCount: Math.min(50, 12 + input.treo),
      highlightKpi: "ai",
    };
  }

  if (input.treo > 0) {
    return {
      pressure,
      aiActive: false,
      aiLabel,
      insight:
        input.treo >= 10
          ? `Áp lực cao: ${input.treo} việc treo cần xử lý trước khi hết ca.`
          : `${input.treo} việc treo — ưu tiên giao việc hoặc đóng việc.`,
      href: "/treo",
      cta: "Xử lý việc treo",
      ariaLabel: `${input.treo} việc treo. Bấm để mở danh sách việc treo.`,
      severity: input.treo >= 15 ? "critical" : "warn",
      particleCount: Math.min(60, input.treo),
      highlightKpi: "treo",
    };
  }

  if (input.tonWarn > 0) {
    return {
      pressure,
      aiActive: false,
      aiLabel,
      insight: `${input.tonWarn} mặt hàng dưới ngưỡng tồn — cần nhập hoặc đặt hàng.`,
      href: "/tieu-thu",
      cta: "Mở sổ tiêu thụ",
      ariaLabel: `${input.tonWarn} cảnh báo tồn. Bấm để mở sổ tiêu thụ.`,
      severity: input.tonWarn >= 3 ? "critical" : "warn",
      particleCount: 8 + input.tonWarn * 4,
      highlightKpi: "ton",
    };
  }

  if (input.role === "chu_quan" && input.inboxCho > 0) {
    return {
      pressure,
      aiActive: false,
      aiLabel,
      insight: `${input.inboxCho} nhân viên chờ bạn xem xét tài khoản hoặc quyền.`,
      href: "/nguoi",
      cta: "Quản lý người dùng",
      ariaLabel: `${input.inboxCho} nhân viên chờ xem xét. Bấm để mở quản lý người dùng.`,
      severity: "warn",
      particleCount: 10 + input.inboxCho * 2,
      highlightKpi: "inbox",
    };
  }

  if (input.role === "quan_ly" && input.inboxCho > 0) {
    return {
      pressure,
      aiActive: false,
      aiLabel,
      insight: `${input.inboxCho} mục chờ bạn duyệt — AI đề xuất, người quyết định.`,
      href: "/inbox",
      cta: "Duyệt hộp thư",
      ariaLabel: `${input.inboxCho} mục chờ duyệt. Bấm để mở hộp thư.`,
      severity: "warn",
      particleCount: 10 + input.inboxCho * 2,
      highlightKpi: "inbox",
    };
  }

  return {
    pressure,
    aiActive: false,
    aiLabel,
    insight: "Quán ổn định. Hỏi cẩm nang AI khi cần quy trình hoặc gợi ý ca.",
    href: "/sop",
    cta: "Hỏi cẩm nang AI",
    ariaLabel: "Quán ổn định. Bấm để hỏi cẩm nang AI.",
    severity: "ok",
    particleCount: 6,
    highlightKpi: "ok",
  };
}

export function severityColor(severity: OpsPulseSeverity): string {
  if (severity === "critical") return "#d45d4a";
  if (severity === "warn") return "#d4a017";
  return "#c4a574";
}
