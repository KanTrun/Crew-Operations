import type { Metadata, Viewport } from "next";
import { fontClass } from "../ui/fonts";
import { ConditionalShell } from "./ConditionalShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "NHỊP QUÁN",
  description: "Ca làm việc · cẩm nang sống",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#0e0c0a",
  width: "device-width",
  initialScale: 1,
  // Cho phép người dùng zoom — chặn zoom là lỗi tiếp cận.
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={fontClass}>
      <body>
        <a href="#nq-content" className="nq-skip">
          Bỏ qua thanh điều hướng
        </a>
        <ConditionalShell>{children}</ConditionalShell>
      </body>
    </html>
  );
}
