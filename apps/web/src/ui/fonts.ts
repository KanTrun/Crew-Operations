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
 */
import { Fraunces, IBM_Plex_Mono, Source_Sans_3 } from "next/font/google";

export const fontDisplay = Fraunces({
  subsets: ["latin", "latin-ext", "vietnamese"],
  weight: ["400", "600"],
  style: ["normal"],
  variable: "--nq-font-display-var",
  display: "swap",
  fallback: ["Source Serif 4", "Georgia", "serif"],
});

export const fontBody = Source_Sans_3({
  subsets: ["latin", "latin-ext", "vietnamese"],
  weight: ["400", "600"],
  variable: "--nq-font-body-var",
  display: "swap",
  fallback: ["IBM Plex Sans", "system-ui", "sans-serif"],
});

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
