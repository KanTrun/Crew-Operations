import type { Metadata } from "next";
import { ConditionalShell } from "./ConditionalShell";
import { SmoothScroll } from "../ui/SmoothScroll";
import { MotionProvider } from "../ui/motion/MotionProvider";
import { fontClass } from "../ui/fonts";
import "./globals.css";
import "./experience.css";
import "./pos.css";

export const metadata: Metadata = {
  title: "NHỊP QUÁN",
  description: "Ca làm việc · cẩm nang sống",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/favicon.ico",
    apple: "/favicon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={fontClass}>
      {/* suppressHydrationWarning: tiện ích trình duyệt (dịch trang, chặn quảng
          cáo) chèn class/thuộc tính vào <body> TRƯỚC khi React hydrate, làm
          React báo lỗi hydration dù HTML của mình đúng. Chỉ bỏ qua cảnh báo ở
          riêng <body>; mọi phần khác vẫn được kiểm tra nghiêm. */}
      <body suppressHydrationWarning>
        <MotionProvider>
          <SmoothScroll>
            <a href="#nq-content" className="nq-skip">
              Bỏ qua thanh điều hướng
            </a>
            <ConditionalShell>{children}</ConditionalShell>
          </SmoothScroll>
        </MotionProvider>
      </body>
    </html>
  );
}
