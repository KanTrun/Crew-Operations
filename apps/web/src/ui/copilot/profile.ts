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
  /** Danh mục việc AI làm được cho role này (hiện trong khung chat — minh bạch). */
  capabilities: string[];
  /** Danh mục việc AI KHÔNG làm được (hiện khi user hỏi vượt quyền). */
  deniedNote?: string;
}

const STAFF: CopilotProfile = {
  role: "nhan_vien",
  label: "Trợ lý ca làm",
  persona: "nhan_vien",
  accent: "#fbbf24", // amber-400
  quickPrompts: [
    "Bản tin sáng hôm nay",
    "Quy trình mở quán gồm các bước nào?",
    "Báo cáo hao hụt sữa hôm nay",
    "Em cần làm gì trong ca này?",
    "Hướng dẫn vệ sinh máy pha cà phê",
  ],
  greeting:
    "Em chào anh/chị. Em có thể xem bản tin, tra cứu quy trình và kiểm tra hao hụt trong ca. Việc xếp lịch hay duyệt đổi ca cần quản lý thực hiện.",
  allowActionApproval: false,
  showAudit: false,
  capabilities: [
    "Xem bản tin ca",
    "Tra cứu quy trình (SOP)",
    "Xem báo cáo hao hụt",
  ],
  deniedNote:
    "Không xếp lịch, không duyệt đổi ca, không đề xuất luật, không kiểm kê tồn kho — việc này thuộc quản lý/chủ quán.",
};

const MANAGER: CopilotProfile = {
  role: "quan_ly",
  label: "Trợ lý vận hành",
  persona: "quan_ly",
  accent: "#22d3ee", // cyan-400
  quickPrompts: [
    "Xếp lịch tuần sau, ưu tiên Lan ca sáng",
    "Xem xét duyệt đổi ca cho bạn Minh",
    "Tóm tắt bản tin sáng hôm nay",
    "Kiểm tra tồn kho và cảnh báo hết hàng",
    "Đề xuất luật mới từ các lần sửa của chị",
  ],
  greeting:
    "Chào anh/chị. Em hỗ trợ xếp lịch, duyệt đổi ca, bản tin, quy trình, hao hụt, đề xuất quy định và kiểm kê. Mọi thay đổi đều chờ anh/chị duyệt trước khi áp dụng.",
  allowActionApproval: true,
  showAudit: false,
  capabilities: [
    "Xếp lịch tuần (solver)",
    "Duyệt đổi ca",
    "Bản tin + quy trình + hao hụt",
    "Đề xuất luật mới",
    "Kiểm kê tồn kho",
  ],
  deniedNote:
    "Không tự áp dụng thay đổi — mọi đề xuất phải qua anh/chị duyệt (two-phase).",
};

const OWNER: CopilotProfile = {
  role: "chu_quan",
  label: "Trợ lý chủ quán",
  persona: "chu_quan",
  accent: "#a78bfa", // violet-400
  quickPrompts: [
    "Tóm tắt bản tin sáng hôm nay",
    "Xếp lịch tuần sau, ưu tiên Lan ca sáng",
    "Xem xét duyệt đổi ca cho bạn Minh",
    "Báo cáo hao hụt sữa hôm nay",
    "Quy trình mở quán gồm các bước nào?",
  ],
  greeting:
    "Chào anh/chị. Em hỗ trợ toàn bộ nghiệp vụ điều hành: xếp lịch, duyệt đổi ca, kiểm kê và đề xuất quy định. Mọi thay đổi vẫn chờ anh/chị duyệt.",
  allowActionApproval: true,
  showAudit: true,
  capabilities: [
    "Toàn bộ quyền của Quản lý",
    "Xem vết audit (vet)",
  ],
  deniedNote:
    "Không tự áp dụng thay đổi — mọi đề xuất phải qua anh/chị duyệt (two-phase).",
};

const GUEST: CopilotProfile = {
  role: "",
  label: "Trợ lý vận hành",
  persona: "nhan_vien",
  accent: "#fbbf24",
  quickPrompts: [],
  greeting: "Vui lòng đăng nhập để dùng trợ lý vận hành.",
  allowActionApproval: false,
  showAudit: false,
  emptyMessage: "Bạn cần đăng nhập để trò chuyện với trợ lý vận hành.",
  capabilities: [],
};

export function getCopilotProfile(role: Role): CopilotProfile {
  if (role === "chu_quan") return OWNER;
  if (role === "quan_ly") return MANAGER;
  if (role === "nhan_vien") return STAFF;
  return GUEST;
}