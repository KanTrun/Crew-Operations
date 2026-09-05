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

export const HUBS: MapHub[] = [
  {
    id: "ca",
    title: "Ca hôm nay",
    tagline: "Việc đang chạy ngay bây giờ",
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
        href: "/phieu",
        label: "Phiếu",
        desc: "Checklist trong ca — mở ca, làm từng bước, treo nếu kẹt.",
        roles: ["nv"],
      },
      {
        href: "/toi",
        label: "Ca của tôi",
        desc: "Lịch cá nhân tuần này — bạn làm ca nào.",
        roles: ["nv", "ql"],
      },
      {
        href: "/qr",
        label: "Điểm danh QR",
        desc: "Quản lý phát mã · nhân viên quét khi vào ca.",
        roles: ["all"],
      },
    ],
  },
  {
    id: "lich",
    title: "Lịch tuần",
    tagline: "Xếp ca & công bằng",
    color: "#6f9b7a",
    angle: 90,
    pages: [
      {
        href: "/roster",
        label: "Lịch tuần",
        desc: "Lưới ca — ghim, chạy solver CP-SAT, công bố lịch.",
        roles: ["ql"],
      },
      {
        href: "/doi-ca",
        label: "Chợ đổi ca",
        desc: "Ba nhánh phải đồng ý mới đổi được.",
        roles: ["all"],
      },
      {
        href: "/cong-bang",
        label: "Công bằng",
        desc: "So sánh giờ/ca với trung bình nhóm.",
        roles: ["all"],
      },
      {
        href: "/tkb",
        label: "TKB ảnh",
        desc: "Tải ảnh lịch cá nhân để đọc và xác nhận khoảng bận.",
        roles: ["all"],
        agent: "Đọc lịch bận",
      },
    ],
  },
  {
    id: "tin",
    title: "Tin & duyệt",
    tagline: "AI đọc — người quyết",
    color: "#d4a017",
    angle: 180,
    pages: [
      {
        href: "/inbox",
        label: "Hộp thư",
        desc: "Tin NV (Telegram/Zalo…) → AI phân loại → quản lý duyệt.",
        roles: ["ql"],
        agent: "AG-MSG",
      },
      {
        href: "/page-quan",
        label: "Page quán",
        desc: "Facebook Page — tin khách, nháp bài (khi nối Meta).",
        roles: ["ql"],
      },
    ],
  },
  {
    id: "hoc",
    title: "Học & vận hành",
    tagline: "Quán nhớ luật, sổ sách, bàn giao",
    color: "#d45d4a",
    angle: 270,
    pages: [
      {
        href: "/cam-nang",
        label: "Cẩm nang",
        desc: "Luật quán sống — đề xuất, duyệt, tập sự, tự tắt.",
        roles: ["ql"],
        agent: "AG-RULE",
      },
      {
        href: "/treo",
        label: "Việc treo",
        desc: "Việc kẹt chưa xử lý xong trong ca.",
        roles: ["ql"],
      },
      {
        href: "/tieu-thu",
        label: "Sổ tiêu thụ",
        desc: "Kiểm kê mặt hàng — không qua agent.",
        roles: ["ql"],
      },
      {
        href: "/hao-phi",
        label: "Hao phí",
        desc: "Ghi hao hụt trong ca.",
        roles: ["ql"],
        agent: "AG-WASTE",
      },
      {
        href: "/sop",
        label: "Hỏi SOP",
        desc: "Hỏi quy trình — trả lời từ phiếu + luật đã duyệt.",
        roles: ["all"],
        agent: "AG-SOP",
      },
      {
        href: "/handover",
        label: "Bàn giao",
        desc: "SBAR 4 phần khi đổi ca.",
        roles: ["nv"],
        agent: "AG-HANDOVER",
      },
      {
        href: "/vet",
        label: "Vết hệ thống",
        desc: "Nhật ký ai làm gì — không xóa.",
        roles: ["ql"],
      },
    ],
  },
];

export const FLOW: FlowStep[] = [
  {
    id: 1,
    title: "Vào ca",
    who: "Nhân viên",
    what: "Quét QR điểm danh — xác nhận đúng ca, đúng giờ.",
    href: "/qr",
    roles: ["nv"],
  },
  {
    id: 2,
    title: "Làm phiếu",
    who: "Nhân viên",
    what: "Mở Phiếu → checklist từng bước. Kẹt thì treo, không im lặng.",
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
  "Một việc một lúc — menu Thêm gom phần ít dùng.",
  "Demo: minh (NV) · lan/hung (QL) · mật khẩu nhipquan.",
];
