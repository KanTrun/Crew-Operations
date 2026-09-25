/**
 * Font self-host qua next/font.
 *
 * Vì sao không dùng <link> tới fonts.googleapis.com:
 *  1. Cổng ra Sprint 8 (§14.9) yêu cầu demo chạy trọn 10 phút khi **đã rút
 *     mạng**. Font tải từ CDN làm chữ rơi về Georgia/system-ui giữa buổi bảo vệ.
 *  2. Phải có subset `vietnamese`, nếu không dấu tiếng Việt render bằng font
 *     fallback và cả trang trông chắp vá.
 *
 * next/font tải font lúc build rồi tự host trong `_next/static`, nên runtime
 * không gọi mạng ra ngoài.
 *
 * Ba font, ba vai — không hơn (xem docs/design-guidelines.md):
 *   fontDisplay  Space Grotesk   tiêu đề trang và tiêu đề khối
 *   fontBody     IBM Plex Sans   chữ đọc chính, nhãn, nút
 *   fontMono     IBM Plex Mono   số trong bảng, mã, thời lượng
 * Không dùng font hệ thống làm font chính: máy nào cũng có, nên không mã hoá
 * được gì và trông giống mọi dashboard khác.
 */
import { IBM_Plex_Mono, IBM_Plex_Sans, Space_Grotesk } from "next/font/google";

/**
 * Tiêu đề. Hình học, hơi nén, có cá tính ở chữ số và dấu câu — đủ khác để tiêu
 * đề trang không lẫn với chữ nội dung, nhưng không trang trí tới mức át số liệu
 * đặt cạnh nó.
 */
export const fontDisplay = Space_Grotesk({
  subsets: ["latin", "latin-ext", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  style: ["normal"],
  variable: "--nq-font-display-var",
  display: "swap",
  fallback: ["Avenir Next", "Segoe UI", "sans-serif"],
});

/**
 * Chữ đọc chính. Cùng họ với font số liệu nên bảng và văn bản quanh nó có chung
 * tỉ lệ chữ; dấu tiếng Việt ở cỡ nhỏ rõ hơn phần lớn font sans hình học.
 */
export const fontBody = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext", "vietnamese"],
  weight: ["400", "500", "600"],
  style: ["normal"],
  variable: "--nq-font-body-var",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
});

/**
 * Số liệu. Bề rộng chữ số bằng nhau (tabular) nên cột số trong bảng không nhảy
 * khi giá trị đổi từ 9 sang 10.
 */
export const fontMono = IBM_Plex_Mono({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500"],
  variable: "--nq-font-mono-var",
  display: "swap",
  fallback: ["ui-monospace", "monospace"],
});

/** Class gộp, gắn vào <html> để mọi biến font có mặt toàn trang. */
export const fontClass = [
  fontDisplay.variable,
  fontBody.variable,
  fontMono.variable,
].join(" ");
