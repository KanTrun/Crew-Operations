"use client";

import Link from "next/link";
import { ReactNode } from "react";

const links = [
  ["/", "Trang chủ"],
  ["/hom-nay", "Hôm nay"],
  ["/roster", "Lịch tuần"],
  ["/phieu", "Phiếu"],
  ["/toi", "Ca của tôi"],
  ["/treo", "Việc treo"],
  ["/inbox", "Hộp thư"],
  ["/cam-nang", "Cẩm nang"],
  ["/sop", "SOP"],
  ["/handover", "Bàn giao"],
  ["/cong-bang", "Công bằng"],
];

export function AppShell({
  children,
  title,
}: {
  children: ReactNode;
  title?: string;
}) {
  return (
    <div style={{ minHeight: "100vh" }}>
      <header
        style={{
          borderBottom: "1px solid var(--nq-line)",
          padding: "0.75rem 1rem",
          display: "flex",
          flexWrap: "wrap",
          gap: "0.75rem 1rem",
          alignItems: "center",
          background: "var(--nq-bg-elevated)",
        }}
      >
        <Link href="/" style={{ fontFamily: "var(--nq-font-display)", color: "var(--nq-ink)", textDecoration: "none", fontSize: "1.15rem" }}>
          NHỊP QUÁN
        </Link>
        <nav style={{ display: "flex", flexWrap: "wrap", gap: "0.65rem", fontSize: "0.88rem" }}>
          {links.map(([href, label]) => (
            <Link key={href} href={href} style={{ color: "var(--nq-ink-muted)" }}>
              {label}
            </Link>
          ))}
        </nav>
      </header>
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "1.25rem 1rem 3rem" }}>
        {title ? (
          <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, marginTop: 0 }}>{title}</h1>
        ) : null}
        {children}
      </div>
    </div>
  );
}
