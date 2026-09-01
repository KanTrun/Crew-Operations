// Profile cấu hình giao diện + giọng nói cho AG-COPILOT theo role.
// Quick prompts / gate hành động / màu sắc đều lấy từ đây để đảm bảo
// mỗi role thấy 1 AG-COPILOT khác nhau.

import type { Role } from "../../lib/session";

export interface CopilotProfile {
  role: Role;
  /** Tên gọi trong header (đã việt hoá). */
  label: string;
  /** Tone nhân vật — ảnh hưởng câu chào + helper copy. */
  persona: "nhan_vien" | "quan_ly" | "chu_quan";
  /** Hex dùng cho accent (chip header, focus border). */
  accent: string;
  /** 5 quick prompt hiện ở thanh dưới body chat. */
  quickPrompts: string[];
  /** Câu chào mặc định (lần đầu mở drawer / page). */
  greeting: string;
  /** ActionProposalCard được phép duyệt / từ chối. */
  allowActionApproval: boolean;
  /** Hiển thị audit / vet link. */
  showAudit: boolean;
  /** Tin nhắn khi user mở drawer nhưng role rỗng. */
  emptyMessage?: string;
}

const STAFF: CopilotProfile = {
  role: "nhan_vien",
  label: "AG-COPILOT · Ca của bạn",
  persona: "nhan_vien",
  accent: "#fbbf24", // amber-400
  quickPrompts: [
    "Ca hôm nay của em gồm những việc gì?",
    "Còn bao nhiêu sữa, có kịp pha tối không?",
    "Hao hụt sữa ca em hôm nay bao nhiêu?",
    "Em xin đổi ca với Hương mai được không?",
    "Quy trình đóng quán gồm những bước nào?",
  ],
  greeting:
    "Em chào anh/chị — em là AG-COPILOT hỗ trợ ca. Anh/chị cứ hỏi việc hôm nay, hao phí, quy trình đóng/mở ca ạ.",
  allowActionApproval: false,
  showAudit: false,
};

const MANAGER: CopilotProfile = {
  role: "quan_ly",
  label: "AG-COPILOT · Điều hành quán",
  persona: "quan_ly",
  accent: "#22d3ee", // cyan-400
  quickPrompts: [
    "Xếp lịch tuần sau, ưu tiên Lan ca sáng",
    "Có bao nhiêu việc đang chờ em duyệt trong inbox?",
    "Tóm tắt bản tin sáng hôm nay",
    "Kiểm kê tồn kho và cảnh báo hết hàng",
    "Chạy 8 bước xét luật cho cẩm nang",
  ],
  greeting:
    "Chào anh/chị — em là AG-COPILOT điều hành. Anh/chị có thể nhờ em xếp lịch, duyệt inbox, kiểm kê hoặc chạy xét luật cẩm nang.",
  allowActionApproval: true,
  showAudit: false,
};

const OWNER: CopilotProfile = {
  role: "chu_quan",
  label: "AG-COPILOT · Chủ quán",
  persona: "chu_quan",
  accent: "#a78bfa", // violet-400
  quickPrompts: [
    "Báo cáo tuần này: doanh thu, hao hụt, lịch treo",
    "Đối chiếu công bằng giữa các ca trong tháng",
    "Vết (audit) có bất thường gì 7 ngày qua?",
    "Menu nào đang bán chạm đáy, cần điều chỉnh?",
    "Nhân sựng nào vắng > 2 ca liên tiếp?",
  ],
  greeting:
    "Chào anh/chị — em là AG-COPILOT của Chủ quán. Mọi số liệu vận hành, audit, fairness, menu đều có thể hỏi em.",
  allowActionApproval: true,
  showAudit: true,
};

const GUEST: CopilotProfile = {
  role: "",
  label: "AG-COPILOT",
  persona: "nhan_vien",
  accent: "#fbbf24",
  quickPrompts: [],
  greeting: "Vui lòng đăng nhập để dùng AG-COPILOT.",
  allowActionApproval: false,
  showAudit: false,
  emptyMessage: "Bạn cần đăng nhập để chat với AG-COPILOT.",
};

export function getCopilotProfile(role: Role): CopilotProfile {
  if (role === "chu_quan") return OWNER;
  if (role === "quan_ly") return MANAGER;
  if (role === "nhan_vien") return STAFF;
  return GUEST;
}