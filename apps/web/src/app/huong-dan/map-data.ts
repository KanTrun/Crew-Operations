export type Role = "nv" | "ql" | "all";

export type MapPage = {
  href: string;
  label: string;
  desc: string;
  roles: Role[];
  agent?: string;
};

export type MapHub = {
  id: string;
  title: string;
  tagline: string;
  color: string;
  angle: number;
  pages: MapPage[];
};

export type FlowStep = {
  id: number;
  title: string;
  who: string;
  what: string;
  href?: string;
  roles: Role[];
};

/**
 * Ba vòng sản phẩm — thứ tự đọc đúng độ quan trọng:
 * 1. Ca làm việc (lõi, luồng 1 ngày)
 * 2. Học (cẩm nang sống — vòng lặp giá trị riêng)
 * 3. Quầy & khách hàng (sản phẩm phụ)
 */
export const HUBS: MapHub[] = [
  {
    id: "ca",
    title: "Vòng 1 — Ca làm việc",
    tagline: "Luồng 1 ngày: vào ca → phiếu → trao đổi → bàn giao",
    color: "#c4a574",
    angle: 0,
    pages: [
      {
        href: "/hom-nay",
        label: "Hôm nay",
        desc: "Bảng điều khiển: ca đang chạy, việc treo, tóm tắt quán.",
        roles: ["all"],
      },
      {
        href: "/toi",
        label: "Ca của tôi",
        desc: "Lịch cá nhân tuần này — bạn làm ca nào.",
        roles: ["nv", "ql"],
      },
      {
        href: "/roster",
        label: "Lịch tuần",
        desc: "Lưới ca — ghim, chạy solver CP-SAT, công bố lịch.",
        roles: ["ql"],
      },
      {
        href: "/qr",
        label: "Điểm danh QR",
        desc: "Quản lý phát mã · nhân viên quét khi vào ca.",
        roles: ["all"],
      },
      {
        href: "/phieu",
        label: "Phiếu",
        desc: "Checklist trong ca — mở ca, làm từng bước, treo nếu kẹt.",
        roles: ["nv"],
      },
      {
        href: "/treo",
        label: "Việc treo",
        desc: "Việc kẹt chưa xử lý xong trong ca.",
        roles: ["ql"],
      },
      {
        href: "/doi-ca",
        label: "Chợ đổi ca",
        desc: "Ba nhánh phải đồng ý mới đổi được.",
        roles: ["all"],
      },
      {
        href: "/inbox",
        label: "Hộp thư",
        desc: "Tin NV (Telegram/Zalo…) → AI phân loại → quản lý duyệt.",
        roles: ["ql"],
        agent: "AG-MSG",
      },
      {
        href: "/handover",
        label: "Bàn giao",
        desc: "SBAR 4 phần khi đổi ca.",
        roles: ["nv"],
        agent: "AG-HANDOVER",
      },
    ],
  },
  {
    id: "hoc",
    title: "Vòng 2 — Học",
    tagline: "Sửa → ghi nhận → ≥3 lần → đề xuất luật → chủ quán chốt",
    color: "#d45d4a",
    angle: 120,
    pages: [
      {
        href: "/tkb",
        label: "TKB ảnh",
        desc: "Tải ảnh lịch cá nhân để AI đọc và xác nhận khoảng bận — lần xếp lịch sau sẽ tránh giờ học.",
        roles: ["all"],
        agent: "AG-TKB",
      },
      {
        href: "/cong-bang",
        label: "Công bằng",
        desc: "So sánh giờ/ca với trung bình nhóm — không xếp hạng tên.",
        roles: ["all"],
      },
      {
        href: "/cam-nang",
        label: "Cẩm nang",
        desc: "Luật quán sống — đề xuất, duyệt, tập sự, tự tắt.",
        roles: ["ql"],
        agent: "AG-RULE",
      },
      {
        href: "/sop",
        label: "Hỏi SOP",
        desc: "Hỏi quy trình — trả lời kèm trích dẫn từ phiếu + luật đã duyệt.",
        roles: ["all"],
        agent: "AG-SOP",
      },
      {
        href: "/ai-learning",
        label: "Học từ phản hồi AI",
        desc: "AI học từ các lần quản lý sửa nội dung AI đề xuất — chủ quán duyệt quy tắc.",
        roles: ["ql"],
      },
      {
        href: "/vet",
        label: "Vết hệ thống",
        desc: "Nhật ký ai làm gì — không xóa.",
        roles: ["ql"],
      },
    ],
  },
  {
    id: "quay",
    title: "Vòng 3 — Quầy & khách hàng",
    tagline: "Sản phẩm phụ: bán hàng, kho, Page quán",
    color: "#6f9b7a",
    angle: 240,
    pages: [
      {
        href: "/quay",
        label: "Ghi đơn quầy",
        desc: "POS chạm món — gửi sang pha chế.",
        roles: ["nv", "ql"],
      },
      {
        href: "/pha",
        label: "Màn pha chế",
        desc: "Barista nhận pha → hoàn tất ghi tiêu thụ BOM.",
        roles: ["nv", "ql"],
      },
      {
        href: "/menu",
        label: "Menu & giá",
        desc: "Chủ quán sửa món, giá, công thức nguyên liệu.",
        roles: ["ql"],
      },
      {
        href: "/tieu-thu",
        label: "Sổ tiêu thụ",
        desc: "Kiểm kê mặt hàng — số lượng, không kế toán.",
        roles: ["ql"],
      },
      {
        href: "/hao-phi",
        label: "Hao phí",
        desc: "Ghi hao hụt trong ca — AI gom cụm nguyên nhân.",
        roles: ["ql"],
        agent: "AG-WASTE",
      },
      {
        href: "/page-quan",
        label: "Page quán",
        desc: "Facebook Page — tin khách, nháp bài (khi nối Meta).",
        roles: ["ql"],
      },
    ],
  },
];

/** Luồng 1 ngày của vòng 1 — đúng thứ tự một ca thật. */
export const FLOW: FlowStep[] = [
  {
    id: 1,
    title: "Vào ca",
    who: "Nhân viên",
    what: "Mở Hôm nay → quét QR điểm danh — xác nhận đúng ca, đúng giờ.",
    href: "/qr",
    roles: ["nv"],
  },
  {
    id: 2,
    title: "Làm phiếu",
    who: "Nhân viên",
    what: "Mở Phiếu → checklist từng bước, chụp ảnh minh chứng. Kẹt thì treo, không im lặng.",
    href: "/phieu",
    roles: ["nv"],
  },
  {
    id: 3,
    title: "Nhắn ý định",
    who: "Nhân viên · kênh tin",
    what: "«Xin nghỉ», «đổi ca»… qua Telegram/Zalo. AI chỉ phân loại, không tự sửa lịch.",
    href: "/inbox",
    roles: ["nv"],
  },
  {
    id: 4,
    title: "Duyệt hộp thư",
    who: "Quản lý",
    what: "Vào Hộp thư → Duyệt / Từ chối. Hiệu lực ca chỉ khi quản lý bấm.",
    href: "/inbox",
    roles: ["ql"],
  },
  {
    id: 5,
    title: "Xếp lịch tuần",
    who: "Quản lý",
    what: "Lịch tuần → ghim ca → chạy solver → công bố. Lõi CP-SAT, không LLM.",
    href: "/roster",
    roles: ["ql"],
  },
  {
    id: 6,
    title: "Xem lịch mình",
    who: "Nhân viên",
    what: "Ca của tôi — biết tuần này làm gì, không hỏi group chat.",
    href: "/toi",
    roles: ["nv"],
  },
  {
    id: 7,
    title: "Cẩm nang học",
    who: "Hệ thống + quản lý",
    what: "Mỗi lần sửa lịch có lý do → luật mới qua 8 bước (khi đủ bằng chứng).",
    href: "/cam-nang",
    roles: ["ql"],
  },
  {
    id: 8,
    title: "Bàn giao ca",
    who: "Nhân viên",
    what: "SBAR cho ca sau — việc treo, sự cố, tồn kho.",
    href: "/handover",
    roles: ["nv"],
  },
];

export const PRINCIPLES = [
  "AI đọc và đề xuất — quản lý duyệt.",
  "Xếp lịch = solver tất định, không LLM ghi DB.",
  "Vòng 2 học từ vòng 1: luật quán sinh ra từ lần sửa thật.",
  "Demo: minh (NV) · lan/hung (QL) · mật khẩu nhipquan.",
];
