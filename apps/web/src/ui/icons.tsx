/**
 * Bộ icon SVG inline.
 *
 * Vì sao không dùng thư viện icon: thêm một dependency runtime cho 9 hình là
 * không đáng, và §10.3 giữ mọi thứ ở mức 0 đồng, không phụ thuộc CDN.
 * Vì sao không dùng emoji: `docs/design-guidelines.md` cấm emoji-as-icon.
 *
 * Mọi icon dùng `currentColor` nên tự đổi màu theo trạng thái active/hover,
 * và mang `aria-hidden` vì nhãn chữ luôn đi kèm.
 */
import type { ReactNode } from "react";

export type IconName =
  | "hom-nay"
  | "phieu"
  | "toi"
  | "treo"
  | "roster"
  | "inbox"
  | "cam-nang"
  | "them"
  | "cong-bang"
  | "copilot"
  | "doi-ca"
  | "chat"
  | "attachment"
  | "microphone"
  | "send"
  | "close"
  | "arrow-left"
  | "bell"
  | "bell-off"
  | "info"
  | "pin"
  | "reply"
  | "edit"
  | "trash"
  | "image"
  | "users"
  | "coffee"
  | "bot"
  | "calendar"
  | "zap"
  | "download"
  | "play"
  | "pause";

const PATHS: Record<IconName, ReactNode> = {
  attachment: <path d="m20.5 11.5-8.9 8.9a6 6 0 0 1-8.5-8.5l9.4-9.4a4 4 0 0 1 5.7 5.7l-9.4 9.4a2 2 0 0 1-2.8-2.8l8.8-8.8" />,
  microphone: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8" /></>,
  send: <path d="m22 2-7 20-4-9-9-4Z M22 2 11 13" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  "arrow-left": <path d="m15 18-6-6 6-6M9 12h10" />,
  bell: <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />,
  "bell-off": <><path d="M13.7 5.1A6 6 0 0 0 6 8c0 7-3 7-3 9h12M18 8c0 3.2.7 5 1.7 6.2M10 21h4M3 3l18 18" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  pin: <path d="m15 4 5 5-3 1-3 5 1 3-2 2-2-4-5-5-4-2 2-2 3 1 5-3 1-3Z" />,
  reply: <path d="M9 14 4 9l5-5M4 9h9a7 7 0 0 1 7 7v2" />,
  edit: <path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10Z M13.5 7.5l3 3" />,
  trash: <><path d="M4 7h16M10 11v5M14 11v5M6 7l1 14h10l1-14M9 7V4h6v3" /></>,
  image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8.5" cy="9" r="1.5" /><path d="m21 15-5-5L5 20" /></>,
  users: <><circle cx="9" cy="8" r="3" /><path d="M3 20a6 6 0 0 1 12 0M16 11a3 3 0 1 0 0-6M18 14a5 5 0 0 1 3 6" /></>,
  coffee: <><path d="M5 8h12v6a5 5 0 0 1-5 5H10a5 5 0 0 1-5-5Z M17 10h2a3 3 0 0 1 0 6h-2M8 4v2M12 3v3" /></>,
  bot: <><rect x="4" y="7" width="16" height="12" rx="3" /><path d="M12 3v4M8 12h.01M16 12h.01M8 16h8" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>,
  zap: <path d="m13 2-9 12h7l-1 8 9-12h-7Z" />,
  download: <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 21h14" />,
  play: <path d="m8 5 11 7-11 7Z" />,
  pause: <path d="M8 5v14M16 5v14" />,
  // Bong bóng hội thoại — chat nội bộ
  chat: (
    <>
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z" />
    </>
  ),
  // Mặt trời trên đường chân trời — bảng "hôm nay"
  "hom-nay": (
    <>
      <circle cx="12" cy="11" r="3.4" />
      <path d="M12 3.5v2M12 16.5v1M4.6 11h2M17.4 11h2M6.8 5.8l1.4 1.4M15.8 7.2l1.4-1.4" />
      <path d="M3 20.5h18" />
    </>
  ),
  // Kẹp giấy có dấu tích — phiếu vận hành
  phieu: (
    <>
      <path d="M9 4.5h6a1 1 0 0 1 1 1v1H8v-1a1 1 0 0 1 1-1Z" />
      <path d="M8 6.5H6.5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1v-11a1 1 0 0 0-1-1H16" />
      <path d="M8.8 12.6l1.8 1.8 3.8-3.8" />
    </>
  ),
  // Người kèm đồng hồ — ca của tôi
  toi: (
    <>
      <circle cx="10" cy="8" r="3.2" />
      <path d="M4.5 19.5c0-3 2.5-5.2 5.5-5.2 1 0 1.9.2 2.7.6" />
      <circle cx="16.8" cy="16.8" r="3.7" />
      <path d="M16.8 15.2v1.8l1.4.9" />
    </>
  ),
  // Cờ — việc treo lại
  treo: (
    <>
      <path d="M6 20.5V4.2" />
      <path d="M6 4.8h9.6l-1.7 3.4 1.7 3.4H6" />
    </>
  ),
  // Lưới tuần — lịch tuần
  roster: (
    <>
      <rect x="3.5" y="5.5" width="17" height="14" rx="1.4" />
      <path d="M3.5 10h17M9 5.5v14M14.8 5.5v14" />
      <path d="M7.5 3.5v3M16.5 3.5v3" />
    </>
  ),
  // Khay thư — hộp thư ràng buộc
  inbox: (
    <>
      <path d="M3.6 13.2 6 6.2a1 1 0 0 1 .95-.7h10.1a1 1 0 0 1 .95.7l2.4 7" />
      <path d="M3.6 13.2h4.2l1 2.3h6.4l1-2.3h4.2v4.6a1 1 0 0 1-1 1H4.6a1 1 0 0 1-1-1Z" />
    </>
  ),
  // Sách mở — cẩm nang sống
  "cam-nang": (
    <>
      <path d="M12 6.6C10.4 5.4 8.3 5 5.4 5.2a.9.9 0 0 0-.9.9v10.5a.9.9 0 0 0 1 .9c2.6-.2 4.6.2 6.5 1.3" />
      <path d="M12 6.6c1.6-1.2 3.7-1.6 6.6-1.4a.9.9 0 0 1 .9.9v10.5a.9.9 0 0 1-1 .9c-2.6-.2-4.6.2-6.5 1.3" />
      <path d="M12 6.6v12.2" />
    </>
  ),
  // Cân — bảng công bằng
  "cong-bang": (
    <>
      <path d="M12 4.5v14.8M7.5 19.3h9" />
      <path d="M12 6.6 5 8.2M12 6.6l7 1.6" />
      <path d="M2.8 12.4a2.2 2.2 0 0 0 4.4 0L5 8.2Z" />
      <path d="M16.8 12.4a2.2 2.2 0 0 0 4.4 0L19 8.2Z" />
    </>
  ),
  // Ba chấm — thêm
  them: (
    <>
      <circle cx="6" cy="12" r="1.4" />
      <circle cx="12" cy="12" r="1.4" />
      <circle cx="18" cy="12" r="1.4" />
    </>
  ),
  // Tia lọc trong bong bóng — trợ lý AI
  copilot: (
    <>
      <path d="M4 5h16v10H13l-4 4v-4H4z" />
      <path d="M12 8l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" />
    </>
  ),
  // Hai mũi tên đổi chiều — đổi ca
  "doi-ca": (
    <>
      <path d="M7 8h10l-3-3" />
      <path d="M17 16H7l3 3" />
    </>
  ),
};

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      className="nq-icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/** Suy icon từ href, để bảng điều hướng chỉ cần khai href + label. */
export function iconForHref(href: string): IconName {
  const key = href.replace(/^\//, "") as IconName;
  return key in PATHS ? key : "them";
}
