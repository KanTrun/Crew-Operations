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

export const btnSecondary: CSSProperties = { ...btnGhost };

type BtnVariant = "primary" | "ghost" | "danger";

function btnClass(variant: BtnVariant, block?: boolean) {
  const v =
    variant === "primary" ? "nq-btn-primary" : variant === "danger" ? "nq-btn-danger" : "nq-btn-ghost";
  return block ? `nq-btn ${v} nq-btn-block` : `nq-btn ${v}`;
}

export function BtnLink({
  href,
  variant = "primary",
  children,
  block,
}: {
  href: string;
  variant?: BtnVariant;
  children: ReactNode;
  block?: boolean;
}) {
  return (
    <Link href={href} className={btnClass(variant, block)}>
      {children}
    </Link>
  );
}

export function PageActions({ children }: { children: ReactNode }) {
  return <div className="nq-page-actions">{children}</div>;
}

export function EditorialBanner({
  wordmark = "NHỊP QUÁN",
  status,
  meta,
}: {
  wordmark?: string;
  status: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <section className="nq-banner" aria-label="Tình trạng quán">
      <div className="nq-banner-inner">
        <p className="nq-banner-wordmark">{wordmark}</p>
        <p className="nq-banner-status">{status}</p>
        {meta ? <p className="nq-banner-meta">{meta}</p> : null}
      </div>
    </section>
  );
}

export function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`nq-skeleton nq-skeleton-line ${className}`.trim()} aria-hidden="true" />;
}

export function SkeletonTile() {
  return (
    <div className="nq-skeleton-tile" aria-hidden="true">
      <div className="nq-skeleton nq-skeleton-line" style={{ width: "40%" }} />
      <div className="nq-skeleton nq-skeleton-line nq-skeleton-line-sm" />
    </div>
  );
}

export function SkeletonRow() {
  return (
    <div className="nq-row">
      <SkeletonTile />
      <SkeletonTile />
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="nq-skeleton-wrap" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="nq-skeleton-item">
          <div className="nq-skeleton nq-skeleton-line" style={{ width: "55%", marginBottom: "0.5rem" }} />
          <div className="nq-skeleton nq-skeleton-line nq-skeleton-line-sm" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonPage({ tiles = true }: { tiles?: boolean }) {
  return (
    <div className="nq-skeleton-wrap" aria-live="polite" aria-busy="true">
      <SkeletonLine />
      <SkeletonLine className="nq-skeleton-line-sm" />
      {tiles ? <SkeletonRow /> : null}
    </div>
  );
}

/** Shimmer load — không dùng Empty cho trạng thái đang fetch */
export function Loading({
  children,
  skeleton = "page",
}: {
  children?: ReactNode;
  skeleton?: "page" | "list" | "tiles" | "text";
}) {
  const label = children ? (
    <span className="nq-muted" style={{ display: "block", marginBottom: "0.65rem" }}>
      {children}
    </span>
  ) : null;

  if (skeleton === "list") {
    return (
      <div aria-live="polite" aria-busy="true">
        {label}
        <SkeletonList />
      </div>
    );
  }
  if (skeleton === "tiles") {
    return (
      <div aria-live="polite" aria-busy="true">
        {label}
        <SkeletonRow />
      </div>
    );
  }
  if (skeleton === "text") {
    return (
      <div className="nq-skeleton-wrap" aria-live="polite" aria-busy="true">
        <SkeletonLine />
        <SkeletonLine className="nq-skeleton-line-sm" />
      </div>
    );
  }
  return (
    <div aria-live="polite" aria-busy="true">
      {label}
      <SkeletonPage />
    </div>
  );
}

export function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="nq-progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className="nq-progress-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function AuthGate() {
  return (
    <div className="nq-page">
      <Kicker>Cần phiên làm việc</Kicker>
      <h1>Đăng nhập để tiếp tục</h1>
      <p className="nq-muted">Trang này đọc dữ liệu quán qua phiên của bạn.</p>
      <PageActions>
        <BtnLink href="/login">Đăng nhập</BtnLink>
      </PageActions>
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
