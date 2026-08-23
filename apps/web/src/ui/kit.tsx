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
  borderRadius: "var(--nq-radius-pill)",
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
  // Ô nhập giữ bo góc 6px: bo bubble ở input làm con trỏ và text lệch tâm.
  borderRadius: "var(--nq-radius)",
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

/**
 * Ngăn kỹ thuật — nơi duy nhất được phép chứa mã nội bộ, JSON hợp đồng,
 * trạng thái solver. Mặc định đóng: hero và thân trang chỉ nói tiếng Việt.
 */
export function TechnicalDrawer({
  summary = "Chi tiết kỹ thuật",
  lines = [],
  children,
}: {
  summary?: string;
  lines?: string[];
  children?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  if (lines.length === 0 && !children) return null;
  return (
    <div className="nq-drawer">
      <button type="button" className="nq-drawer-trigger" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {summary}
        <span aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      {open && lines.length > 0 ? (
        <ul className="nq-drawer-panel">
          {lines.map((line, i) => (
            <li key={`${i}-${line}`}>{line}</li>
          ))}
        </ul>
      ) : null}
      {open && children ? <div className="nq-drawer-block">{children}</div> : null}
    </div>
  );
}

/**
 * Mã dùng-một-lần hiển thị dạng che. Bấm để sao chép vào clipboard, không in
 * nguyên mã lên màn hình — màn hình quán ai đi qua cũng đọc được.
 */
export function MaskedCode({
  code,
  masked,
  label = "Mã một lần",
}: {
  code: string;
  masked: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="nq-masked">
      <span className="nq-masked-code" aria-label={`${label} đã được che`}>
        {masked}
      </span>
      <Btn variant="ghost" onClick={copy}>
        {copied ? "Đã sao chép mã" : "Sao chép mã"}
      </Btn>
    </div>
  );
}

/** Chú thích ngắn dưới ô nhập — nói rõ nhập gì, không nói tên field kỹ thuật. */
export function Hint({ children }: { children: ReactNode }) {
  return <p className="nq-hint">{children}</p>;
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
        {label}
        <SkeletonLine />
        <SkeletonLine className="nq-skeleton-line-sm" />
      </div>
    );
  }
  if (skeleton === "list") {
    return (
      <div aria-live="polite" aria-busy="true">
        {label}
        <SkeletonList />
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

export const textareaStyle: CSSProperties = {
  ...inputStyle,
  minHeight: 96,
  resize: "vertical",
  lineHeight: 1.45,
};

export function Btn({
  variant = "primary",
  block,
  disabled,
  type = "button",
  onClick,
  children,
  title,
  className = "",
}: {
  variant?: BtnVariant;
  block?: boolean;
  disabled?: boolean;
  type?: "button" | "submit";
  onClick?: () => void;
  children: ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      className={`${btnClass(variant, block)} ${className}`.trim()}
    >
      {children}
    </button>
  );
}

export function PageHeader({
  kicker,
  title,
  meta,
}: {
  kicker: string;
  title: string;
  meta?: ReactNode;
}) {
  return (
    <header className="nq-page-head">
      <Kicker>{kicker}</Kicker>
      <h1>{title}</h1>
      {meta ? <p className="nq-muted nq-page-head-meta">{meta}</p> : null}
    </header>
  );
}

export function TabBar({ children }: { children: ReactNode }) {
  return <div className="nq-tab-bar">{children}</div>;
}

export function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button type="button" className="nq-tab" data-on={active ? "1" : "0"} onClick={onClick}>
      {children}
    </button>
  );
}

export function InlineActions({ children }: { children: ReactNode }) {
  return <div className="nq-inline-actions">{children}</div>;
}

export function OpsCard({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="nq-ops-card">
      {eyebrow ? <p className="nq-ops-eyebrow">{eyebrow}</p> : null}
      {title ? <h2 className="nq-ops-title">{title}</h2> : null}
      {children}
    </div>
  );
}

export function StepDone({ label, timingMs }: { label: string; timingMs?: number }) {
  return (
    <div className="nq-step-done">
      <span className="nq-step-check" aria-hidden="true">
        ✓
      </span>
      <span className="nq-step-label">{label}</span>
      {timingMs != null ? (
        <span className="nq-step-time">{(timingMs / 1000).toFixed(1)}s</span>
      ) : null}
    </div>
  );
}

export function FixedBottomBar({ children }: { children: ReactNode }) {
  return <div className="nq-fixed-bottom">{children}</div>;
}

export function StatusChip({
  tone = "default",
  children,
}: {
  tone?: "default" | "warn" | "ok" | "danger";
  children: ReactNode;
}) {
  return <span className={`nq-chip nq-chip--${tone}`}>{children}</span>;
}

export function Toolbar({ children }: { children: ReactNode }) {
  return <div className="nq-toolbar">{children}</div>;
}

export function Notice({ children }: { children: ReactNode }) {
  return <p className="nq-notice">{children}</p>;
}

export function LinkGrid({ children }: { children: ReactNode }) {
  return <div className="nq-link-grid">{children}</div>;
}

export function LinkTile({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="nq-link-tile">
      {children}
    </Link>
  );
}

function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="nq-list nq-list--load" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="nq-skeleton nq-item" style={{ minHeight: 72 }} />
      ))}
    </div>
  );
}
