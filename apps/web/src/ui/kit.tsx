"use client";

import Link from "next/link";
import { CSSProperties, ReactNode, useState } from "react";

export const btnPrimary: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 44,
  padding: "0.75rem 1.35rem",
  background: "var(--nq-accent)",
  color: "var(--nq-accent-ink)",
  border: "none",
  borderRadius: 4,
  fontWeight: 600,
  fontSize: "1rem",
  cursor: "pointer",
  fontFamily: "var(--nq-font-body)",
  textDecoration: "none",
};

export const btnGhost: CSSProperties = {
  ...btnPrimary,
  background: "color-mix(in srgb, var(--nq-surface) 88%, transparent)",
  color: "var(--nq-ink)",
  border: "1px solid var(--nq-line)",
  backdropFilter: "blur(8px)",
};

export const btnSecondary: CSSProperties = { ...btnGhost };

export const btnDanger: CSSProperties = {
  ...btnPrimary,
  background: "var(--nq-danger)",
  color: "#fff8f4",
};

export const inputStyle: CSSProperties = {
  width: "100%",
  minHeight: 48,
  padding: "0.65rem 0.85rem",
  background: "color-mix(in srgb, var(--nq-bg-elevated) 90%, transparent)",
  border: "1px solid var(--nq-line)",
  color: "var(--nq-ink)",
  borderRadius: 4,
  fontFamily: "var(--nq-font-body)",
  fontSize: "1rem",
};

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

export function Kicker({ children }: { children: ReactNode }) {
  return <p className="nq-kicker">{children}</p>;
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
    <section className="nq-banner" aria-label="Tình trạng">
      <div className="nq-banner-inner">
        <p className="nq-banner-wordmark">{wordmark}</p>
        <p className="nq-banner-status">{status}</p>
        {meta ? <p className="nq-banner-meta">{meta}</p> : null}
      </div>
    </section>
  );
}

export function BentoTile({
  value,
  label,
  accent,
  large,
  href,
}: {
  value: ReactNode;
  label: string;
  accent?: "warn" | "ok" | "default";
  large?: boolean;
  href?: string;
}) {
  const cls = `nq-bento-tile${large ? " nq-bento-tile--lg" : ""}${accent ? ` nq-bento-tile--${accent}` : ""}`;
  const inner = (
    <>
      <strong className="nq-bento-value">{value}</strong>
      <span className="nq-bento-label">{label}</span>
    </>
  );
  if (href) {
    return (
      <Link href={href} className={cls}>
        {inner}
      </Link>
    );
  }
  return <div className={cls}>{inner}</div>;
}

export function TechnicalDrawer({
  summary = "Chi tiết kỹ thuật",
  lines,
}: {
  summary?: string;
  lines: string[];
}) {
  const [open, setOpen] = useState(false);
  if (lines.length === 0) return null;
  return (
    <div className="nq-drawer">
      <button type="button" className="nq-drawer-trigger" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {summary}
        <span aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      {open ? (
        <ul className="nq-drawer-panel">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
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

function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`nq-skeleton nq-skeleton-line ${className}`.trim()} aria-hidden="true" />;
}

function SkeletonBento() {
  return (
    <div className="nq-bento nq-bento--load" aria-hidden="true">
      <div className="nq-skeleton nq-bento-tile nq-bento-tile--lg" />
      <div className="nq-skeleton nq-bento-tile" />
      <div className="nq-skeleton nq-bento-tile" />
    </div>
  );
}

export function Loading({
  children,
  skeleton = "page",
}: {
  children?: ReactNode;
  skeleton?: "page" | "bento" | "list" | "text";
}) {
  const label = children ? <span className="nq-load-label">{children}</span> : null;
  if (skeleton === "bento") {
    return (
      <div aria-live="polite" aria-busy="true">
        {label}
        <SkeletonBento />
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
      <SkeletonBento />
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

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="nq-field">
      <span>{label}</span>
      {children}
    </label>
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
