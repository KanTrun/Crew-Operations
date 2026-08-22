"use client";

import Link from "next/link";
import { CSSProperties, ReactNode } from "react";

export const btnPrimary: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 44,
  padding: "0.7rem 1.15rem",
  background: "var(--nq-accent)",
  color: "var(--nq-accent-ink)",
  border: "none",
  borderRadius: 2,
  fontWeight: 600,
  fontSize: "1rem",
  cursor: "pointer",
  fontFamily: "var(--nq-font-body)",
};

export const btnGhost: CSSProperties = {
  ...btnPrimary,
  background: "var(--nq-surface)",
  color: "var(--nq-ink)",
  border: "1px solid var(--nq-line)",
};

export const btnDanger: CSSProperties = {
  ...btnPrimary,
  background: "var(--nq-danger)",
  color: "#fff8f4",
};

export const inputStyle: CSSProperties = {
  width: "100%",
  minHeight: 44,
  padding: "0.6rem 0.75rem",
  background: "var(--nq-bg-elevated)",
  border: "1px solid var(--nq-line)",
  color: "var(--nq-ink)",
  borderRadius: 2,
  fontFamily: "var(--nq-font-body)",
  fontSize: "1rem",
};

export function Kicker({ children }: { children: ReactNode }) {
  return <p className="nq-kicker">{children}</p>;
}

export function Alert({
  kind = "err",
  children,
}: {
  kind?: "err" | "ok" | "info";
  children: ReactNode;
}) {
  const color =
    kind === "ok" ? "var(--nq-ok)" : kind === "info" ? "var(--nq-accent)" : "var(--nq-danger)";
  return (
    <p role={kind === "err" ? "alert" : undefined} className="nq-alert" style={{ borderColor: color, color }}>
      {children}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="nq-empty">{children}</p>;
}

/** Chỗ giữ trong lúc chờ API — tránh nháy "chưa có dữ liệu" khi thật ra đang tải. */
export function Loading({ children = "Đang tải…" }: { children?: ReactNode }) {
  return (
    <p className="nq-empty" aria-live="polite" aria-busy="true">
      {children}
    </p>
  );
}

export function AuthGate() {
  return (
    <div className="nq-page">
      <Kicker>Cần phiên làm việc</Kicker>
      <h1>Đăng nhập để tiếp tục</h1>
      <p className="nq-muted">Trang này đọc dữ liệu quán qua phiên của bạn.</p>
      <p style={{ marginTop: "1.25rem" }}>
        <Link href="/login" style={btnPrimary}>
          Đăng nhập
        </Link>
      </p>
    </div>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="nq-field">
      <span>{label}</span>
      {children}
    </label>
  );
}
