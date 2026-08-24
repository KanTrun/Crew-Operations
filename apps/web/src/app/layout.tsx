import type { Metadata, Viewport } from "next";
import { fontClass } from "../ui/fonts";
import { ConditionalShell } from "./ConditionalShell";
import { SmoothScroll } from "../ui/SmoothScroll";
import { CustomCursor } from "../ui/CustomCursor";
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
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={fontClass}>
      <body className="cursor-none">
        <CustomCursor />
        <SmoothScroll>
          <a href="#nq-content" className="nq-skip">
            Bỏ qua thanh điều hướng
          </a>
          <ConditionalShell>{children}</ConditionalShell>
        </SmoothScroll>
      </body>
    </html>
  );
}
