import type { Metadata } from "next";
import { ConditionalShell } from "./ConditionalShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "NHỊP QUÁN",
  description: "Ca làm việc · cẩm nang sống",
  manifest: "/manifest.webmanifest",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <a href="#nq-content" className="nq-skip">
          Bỏ qua thanh điều hướng
        </a>
        <ConditionalShell>{children}</ConditionalShell>
      </body>
    </html>
  );
}
