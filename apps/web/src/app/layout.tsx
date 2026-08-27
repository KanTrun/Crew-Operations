import type { Metadata } from "next";
import { ConditionalShell } from "./ConditionalShell";
<<<<<<< Updated upstream
=======
import { SmoothScroll } from "../ui/SmoothScroll";
>>>>>>> Stashed changes
import "./globals.css";

export const metadata: Metadata = {
  title: "NHỊP QUÁN",
  description: "Ca làm việc · cẩm nang sống",
  manifest: "/manifest.webmanifest",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
<<<<<<< Updated upstream
    <html lang="vi">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Source+Sans+3:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <ConditionalShell>{children}</ConditionalShell>
=======
    <html lang="vi" className={fontClass}>
      <body>
        <SmoothScroll>
          <a href="#nq-content" className="nq-skip">
            Bỏ qua thanh điều hướng
          </a>
          <ConditionalShell>{children}</ConditionalShell>
        </SmoothScroll>
>>>>>>> Stashed changes
      </body>
    </html>
  );
}
