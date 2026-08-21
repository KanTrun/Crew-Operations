import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NHỊP QUÁN",
  description: "Hệ điều hành quán cà phê — ca làm việc · cẩm nang sống",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          fontFamily: "Georgia, 'Times New Roman', serif",
          background:
            "radial-gradient(ellipse at 20% 0%, #2a2118 0%, #12100e 45%, #0a0908 100%)",
          color: "#f3e6d4",
        }}
      >
        {children}
      </body>
    </html>
  );
}
