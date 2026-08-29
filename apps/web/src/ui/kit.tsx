"use client";

import Link from "next/link";
import { CSSProperties, ReactNode, useCallback, useEffect, useRef, useState } from "react";

export const inputStyle: CSSProperties = {
  width: "100%",
  padding: "0.75rem 1rem",
  backgroundColor: "var(--nq-surface-hi)",
  color: "var(--nq-fg)",
  border: "2px solid var(--nq-dim)",
  fontFamily: "var(--nq-font-mono)",
  fontSize: "1rem",
  boxSizing: "border-box",
};

export const textareaStyle: CSSProperties = {
  ...inputStyle,
  minHeight: "80px",
  resize: "vertical",
};

export const btnPrimary: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "0.75rem 1.5rem",
  backgroundColor: "var(--nq-copper)",
  color: "var(--nq-accent-ink)",
  border: "2px solid var(--nq-copper)",
  fontWeight: "900",
  textTransform: "uppercase",
  letterSpacing: "0.1em",
  boxShadow: "6px 6px 0px 0px var(--nq-copper-dim)",
  cursor: "pointer",
  textDecoration: "none",
};

export const btnGhost: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "0.75rem 1.5rem",
  backgroundColor: "transparent",
  color: "var(--nq-fg)",
  border: "2px solid var(--nq-dim)",
  fontWeight: "900",
  textTransform: "uppercase",
  letterSpacing: "0.1em",
  cursor: "pointer",
  textDecoration: "none",
};

export const btnSecondary: CSSProperties = btnGhost;

export const btnDanger: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "0.75rem 1.5rem",
  backgroundColor: "var(--nq-red)",
  color: "#ffffff",
  border: "2px solid var(--nq-red)",
  fontWeight: "900",
  textTransform: "uppercase",
  letterSpacing: "0.1em",
  boxShadow: "6px 6px 0px 0px var(--nq-red-dim)",
  cursor: "pointer",
  textDecoration: "none",
};

type BtnVariant = "primary" | "ghost" | "danger";

function btnClass(variant: BtnVariant, block?: boolean) {
  const base =
    "font-black uppercase tracking-widest py-3 px-6 md:py-4 md:px-8 border-2 transition-all text-center inline-flex items-center justify-center gap-2";
  const w = block ? "w-full" : "";

  if (variant === "primary") {
    return `${base} ${w} nq-ink-on-solid bg-[var(--nq-copper)] border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)] disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0`;
  }
  if (variant === "danger") {
    return `${base} ${w} nq-ink-on-solid bg-[var(--nq-red)] border-[var(--nq-red)] hover:bg-transparent hover:text-[var(--nq-red)] shadow-[8px_8px_0px_0px_var(--nq-red-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-red-dim)] disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0`;
  }
  return `${base} ${w} bg-transparent text-[var(--nq-fg)] border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] disabled:opacity-50`;
}

export function BtnLink({
  href,
  variant = "primary",
  children,
  block,
  className = "",
}: {
  href: string;
  variant?: BtnVariant;
  children: ReactNode;
  block?: boolean;
  className?: string;
}) {
  return (
    <Link href={href} className={className || btnClass(variant, block)}>
      {children}
    </Link>
  );
}

export function PageActions({ children }: { children: ReactNode }) {
  return <div className="flex flex-col sm:flex-row gap-4 mt-8">{children}</div>;
}

export function Kicker({ children }: { children: ReactNode }) {
  return <p className="text-sm font-mono text-[var(--nq-copper)] uppercase tracking-widest mb-2">{children}</p>;
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
    <section className="nq-ink-on-solid bg-[var(--nq-copper)] p-6 md:p-10 mb-10 md:mb-12 shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] w-full" aria-label="Tình trạng">
      <div className="w-full max-w-none">
        <p className="text-sm font-mono uppercase tracking-widest mb-3 opacity-80">{wordmark}</p>
        <p className="text-3xl md:text-5xl font-black uppercase tracking-tighter mb-4 leading-none">{status}</p>
        {meta ? <p className="text-base md:text-lg font-mono opacity-90 max-w-3xl">{meta}</p> : null}
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
  const bg =
    accent === "warn"
      ? "nq-ink-on-solid bg-[var(--nq-warn)]"
      : accent === "ok"
        ? "nq-ink-on-solid bg-[var(--nq-green)]"
        : "bg-[var(--nq-surface-hi)] text-[var(--nq-fg)] border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)]";

  const span = large
    ? "nq-bento-tile nq-bento-tile--lg col-span-12 sm:col-span-6 lg:col-span-8 lg:row-span-2 min-h-[200px]"
    : "nq-bento-tile col-span-12 sm:col-span-6 lg:col-span-4 min-h-[140px]";
  const cls = `${span} flex flex-col justify-between p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] transition-all ${bg}`;

  const inner = (
    <>
      <strong className={`nq-bento-value font-black ${large ? "text-6xl md:text-8xl" : "text-4xl"} mb-4 block`}>{value}</strong>
      <span className="nq-bento-label text-sm font-mono uppercase tracking-widest opacity-80">{label}</span>
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
  className = "",
}: {
  summary?: string;
  lines?: string[];
  children?: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  if (lines.length === 0 && !children) return null;
  return (
    <div className={`mt-8 ${className}`.trim()}>
      <button 
        type="button" 
        className="w-full flex justify-between items-center bg-[var(--nq-surface)] border-2 border-dashed border-[var(--nq-dim)] p-4 text-[var(--nq-dim)] font-mono text-sm hover:border-[var(--nq-fg)] hover:text-[var(--nq-fg)] transition-colors" 
        onClick={() => setOpen((v) => !v)} 
        aria-expanded={open}
      >
        <span>{summary}</span>
        <span aria-hidden="true" className="font-bold">{open ? "−" : "+"}</span>
      </button>
      {open && lines.length > 0 ? (
        <ul className="bg-[var(--nq-surface-hi)] border-2 border-t-0 border-[var(--nq-dim)] p-4 font-mono text-sm text-[var(--nq-dim)] space-y-2">
          {lines.map((line, i) => (
            <li key={`${i}-${line}`}>{line}</li>
          ))}
        </ul>
      ) : null}
      {open && children ? <div className="bg-[var(--nq-surface-hi)] border-2 border-t-0 border-[var(--nq-dim)] p-4">{children}</div> : null}
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
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex items-center gap-4 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-4">
      <span className="font-mono text-2xl tracking-widest text-[var(--nq-fg)]" aria-label={`${label} đã được che`}>
        {masked}
      </span>
      <button 
        type="button"
        onClick={copy}
        className="ml-auto bg-transparent text-[var(--nq-dim)] font-bold uppercase tracking-widest py-2 px-4 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all"
      >
        {copied ? "Đã chép" : "Sao chép"}
      </button>
    </div>
  );
}

/** Chú thích ngắn dưới ô nhập — nói rõ nhập gì, không nói tên field kỹ thuật. */
export function Hint({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`text-xs font-mono text-[var(--nq-dim)] mt-2 ${className}`.trim()}>{children}</p>;
}

export function Alert({
  kind = "err",
  children,
  className = "",
}: {
  kind?: "err" | "ok" | "info";
  children: ReactNode;
  className?: string;
}) {
  const tone = kind === "ok" ? "nq-alert--ok" : kind === "info" ? "nq-alert--info" : "nq-alert--err";
  return (
    <div
      role={kind === "err" ? "alert" : undefined}
      className={`nq-alert ${tone} ${className}`.trim()}
    >
      {children}
    </div>
  );
}

export function Empty({ children, title = "Không có dữ liệu" }: { children: ReactNode; title?: string }) {
  return (
    <div className="bg-[var(--nq-surface)] border-2 border-dashed border-[var(--nq-dim)] p-8 flex flex-col items-center justify-center text-center">
      <h3 className="text-xl font-bold mb-2 text-[var(--nq-fg)]">{title}</h3>
      <p className="text-[var(--nq-dim)] font-mono text-sm max-w-md">{children}</p>
    </div>
  );
}

function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`h-4 bg-[var(--nq-dim)]/20 rounded ${className}`.trim()} aria-hidden="true" />;
}

function SkeletonBento() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" aria-hidden="true">
      <div className="h-48 bg-[var(--nq-dim)]/20 rounded lg:col-span-2" />
      <div className="h-48 bg-[var(--nq-dim)]/20 rounded" />
      <div className="h-48 bg-[var(--nq-dim)]/20 rounded" />
    </div>
  );
}

function SkeletonStats({ cells = 4 }: { cells?: number }) {
  return (
    <div className="flex flex-wrap gap-4" aria-hidden="true">
      {Array.from({ length: cells }, (_, i) => (
        <div key={i} className="w-32 h-24 bg-[var(--nq-dim)]/20 rounded" />
      ))}
    </div>
  );
}

function SkeletonRows({ rows = 4, groups = 1 }: { rows?: number; groups?: number }) {
  return (
    <div aria-hidden="true" className="space-y-8">
      {Array.from({ length: groups }, (_, g) => (
        <div key={g} className="space-y-4">
          <div className="h-6 w-1/3 bg-[var(--nq-dim)]/20 rounded mb-4" />
          {Array.from({ length: rows }, (_, i) => (
            <div key={i} className="flex justify-between items-center p-4 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)]">
              <div className="space-y-2 w-1/2">
                <div className="h-5 bg-[var(--nq-dim)]/20 rounded w-full" />
                <div className="h-4 bg-[var(--nq-dim)]/20 rounded w-2/3" />
              </div>
              <div className="h-8 w-16 bg-[var(--nq-dim)]/20 rounded" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function SkeletonCard({ cards = 1, form }: { cards?: number; form?: boolean }) {
  return (
    <div aria-hidden="true" className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {Array.from({ length: cards }, (_, i) => (
        <div key={i} className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6">
          <div className="h-4 w-1/4 bg-[var(--nq-dim)]/20 rounded mb-4" />
          <div className="h-8 w-2/3 bg-[var(--nq-dim)]/20 rounded mb-6" />
          {form ? (
            <div className="space-y-4">
              <div className="h-12 bg-[var(--nq-dim)]/20 rounded w-full" />
              <div className="h-12 bg-[var(--nq-dim)]/20 rounded w-full" />
              <div className="h-12 bg-[var(--nq-dim)]/20 rounded w-1/3 mt-6" />
            </div>
          ) : (
            <div className="space-y-2">
              <div className="h-4 bg-[var(--nq-dim)]/20 rounded w-full" />
              <div className="h-4 bg-[var(--nq-dim)]/20 rounded w-3/4" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SkeletonTable({ rows = 3 }: { rows?: number }) {
  return (
    <div className="w-full bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)]" aria-hidden="true">
      <div className="flex border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-4 gap-4">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="h-4 bg-[var(--nq-dim)]/20 rounded flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex border-b border-[var(--nq-dim)]/30 p-4 gap-4">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="h-4 bg-[var(--nq-dim)]/20 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export type SkeletonShape = "page" | "bento" | "list" | "text" | "stats" | "rows" | "card" | "form" | "table";

export function Loading({
  children,
  skeleton = "page",
  rows,
  groups,
}: {
  children?: ReactNode;
  skeleton?: SkeletonShape;
  rows?: number;
  groups?: number;
}) {
  const label = children ? <span className="block text-sm font-mono text-[var(--nq-copper)] uppercase tracking-widest mb-4">{children}</span> : null;
  let shape: ReactNode;
  if (skeleton === "bento" || skeleton === "page") shape = <SkeletonBento />;
  else if (skeleton === "text")
    shape = (
      <div className="space-y-2">
        <SkeletonLine />
        <SkeletonLine className="w-1/2" />
      </div>
    );
  else if (skeleton === "list") shape = <SkeletonList rows={rows ?? 3} />;
  else if (skeleton === "stats") shape = <SkeletonStats cells={rows ?? 4} />;
  else if (skeleton === "rows") shape = <SkeletonRows rows={rows ?? 4} groups={groups ?? 1} />;
  else if (skeleton === "card") shape = <SkeletonCard cards={rows ?? 1} />;
  else if (skeleton === "form") shape = <SkeletonCard cards={1} form />;
  else shape = <SkeletonTable rows={rows ?? 3} />;

  return (
    <div aria-live="polite" aria-busy="true" className="animate-pulse">
      {label}
      {shape}
    </div>
  );
}

export function AuthGate() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center bg-[var(--nq-bg)]">
      <h1 className="text-4xl font-black uppercase tracking-tighter text-[var(--nq-fg)] mb-4">Cần phiên làm việc</h1>
      <p className="text-xl text-[var(--nq-dim)] mb-8 max-w-md">Trang này đọc dữ liệu quán qua phiên của bạn. Đăng nhập để tiếp tục.</p>
      <div className="flex flex-col sm:flex-row gap-4">
        <BtnLink href="/login" className="nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-4 px-8 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)]">
          Đăng nhập
        </BtnLink>
        <BtnLink href="/dang-ky" className="bg-transparent text-[var(--nq-fg)] font-black uppercase tracking-widest py-4 px-8 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all">
          Tạo tài khoản
        </BtnLink>
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block mb-4">
      <span className="block text-sm font-bold uppercase tracking-widest text-[var(--nq-dim)] mb-2">{label}</span>
      {children}
    </label>
  );
}

export function ProgressBar({ value, max, className = "" }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className={`w-full h-4 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] overflow-hidden ${className}`.trim()} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className="h-full bg-[var(--nq-copper)] transition-all duration-500 ease-out" style={{ width: `${pct}%` }} />
    </div>
  );
}


/** Vòng xoay nhỏ trong nút đang gửi. `aria-hidden` vì chữ đã đổi thành "Đang…". */
export function Spinner() {
  return <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" aria-hidden="true" />;
}

/**
 * Nút.
 *
 * `busy` gộp bốn việc phải luôn đi cùng nhau khi một nút đang gửi: hiện spinner,
 * đổi chữ sang thể đang-làm, chặn bấm lần hai, và báo cho trình đọc màn hình qua
 * `aria-busy`. Trước đây mỗi trang tự làm ba phần đầu và bỏ quên phần thứ tư.
 */
export function Btn({
  variant = "primary",
  block,
  disabled,
  busy,
  busyLabel,
  type = "button",
  onClick,
  children,
  title,
  className = "",
}: {
  variant?: BtnVariant;
  block?: boolean;
  disabled?: boolean;
  busy?: boolean;
  busyLabel?: string;
  type?: "button" | "submit";
  onClick?: () => void;
  children: ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <button
      type={type}
      disabled={disabled || busy}
      aria-busy={busy ? true : undefined}
      onClick={onClick}
      title={title}
      className={className || btnClass(variant, block)}
    >
      {busy ? <Spinner /> : null}
      {busy ? busyLabel ?? "Đang lưu…" : children}
    </button>
  );
}

/**
 * Số liệu: mono, căn phải, cùng số chữ số thập phân trong một cột.
 *
 * `digits` phải giống nhau cho cả cột — cột số mà dòng thì 3, dòng thì 3.25 làm
 * mắt phải đọc từng ô thay vì quét dọc.
 */
export function Num({
  value,
  digits = 0,
  unit,
  large,
}: {
  value: unknown;
  digits?: number;
  unit?: string;
  large?: boolean;
}) {
  const n = typeof value === "number" ? value : Number(value);
  const text = Number.isFinite(n) ? n.toFixed(digits) : "—";
  return (
    <span className={`font-mono ${large ? "text-2xl font-black" : ""}`}>
      {text}
      {unit ? <span className="text-sm text-[var(--nq-dim)] ml-1">{unit}</span> : null}
    </span>
  );
}

/** Khối chỉ số tóm tắt — đếm từ dữ liệu thật, đặt trên nội dung chính. */
export function StatGrid({ children }: { children: ReactNode }) {
  return <ul className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">{children}</ul>;
}

export function Stat({
  value,
  label,
  tone = "default",
}: {
  value: ReactNode;
  label: string;
  tone?: "default" | "warn" | "ok" | "danger";
}) {
  const bg =
    tone === "warn"
      ? "nq-ink-on-solid bg-[var(--nq-warn)]"
      : tone === "ok"
        ? "nq-ink-on-solid bg-[var(--nq-green)]"
        : tone === "danger"
          ? "nq-ink-on-solid bg-[var(--nq-red)]"
          : "bg-[var(--nq-surface-hi)] text-[var(--nq-fg)] border-2 border-[var(--nq-dim)]";
  return (
    <li className={`flex flex-col p-4 shadow-[4px_4px_0px_0px_var(--nq-copper-dim)] ${bg}`}>
      <span className="text-3xl font-black mb-1 tabular-nums">{value}</span>
      <span className="text-xs font-mono uppercase tracking-widest opacity-80">{label}</span>
    </li>
  );
}

/**
 * Một nhóm bản ghi trong danh sách dài: tiêu đề + số đếm + các dòng cách nhau
 * bằng hairline. Số đếm ở tiêu đề là bắt buộc với danh sách trên 10 dòng.
 */
export function Group({
  title,
  count,
  countLabel = "bản ghi",
  children,
}: {
  title: string;
  count?: number;
  countLabel?: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-8">
      <div className="flex items-center gap-4 mb-4">
        <h3 className="text-xl font-black uppercase text-[var(--nq-fg)]">{title}</h3>
        {typeof count === "number" ? (
          <span className="nq-ink-on-solid text-sm bg-[var(--nq-copper)] px-3 py-1 rounded-full">
            {count} {countLabel}
          </span>
        ) : null}
      </div>
      <ul className="space-y-4">{children}</ul>
    </section>
  );
}

export function Row({
  title,
  sub,
  side,
  actions,
}: {
  title: ReactNode;
  sub?: ReactNode;
  side?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <li className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] gap-4 hover:border-[var(--nq-copper)] transition-colors">
      <div className="flex-1">
        <p className="font-bold text-[var(--nq-fg)] mb-1">{title}</p>
        {sub ? <p className="text-sm font-mono text-[var(--nq-dim)]">{sub}</p> : null}
      </div>
      {side ? <div className="flex items-center gap-4">{side}</div> : null}
      {actions ? <div className="flex items-center gap-2 mt-4 sm:mt-0 w-full sm:w-auto">{actions}</div> : null}
    </li>
  );
}

/** Khối cuối trang: người dùng làm gì tiếp. Không để trang kết thúc bằng danh sách trơ. */
export function NextSteps({
  title = "Làm gì tiếp",
  note,
  children,
}: {
  title?: string;
  note?: string;
  children: ReactNode;
}) {
  return (
    <div className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 md:p-8 mt-12 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
      <h2 className="text-2xl font-black uppercase mb-2 text-[var(--nq-fg)]">{title}</h2>
      {note ? <p className="text-[var(--nq-dim)] font-mono text-sm mb-6 uppercase tracking-widest">{note}</p> : null}
      <div className="flex flex-col sm:flex-row gap-4">
        {children}
      </div>
    </div>
  );
}

export function PageHeader({
  kicker,
  title,
  meta,
  tourId,
}: {
  kicker: string;
  title: string;
  meta?: ReactNode;
  tourId?: string;
}) {
  return (
    <header className="mb-12 ops-animate-in" data-tour={tourId}>
      <p className="text-sm font-mono text-[var(--nq-copper)] uppercase tracking-widest mb-2">{kicker}</p>
      <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-fg)] mb-4">{title}</h1>
      {meta ? <p className="text-[var(--nq-dim)] font-mono text-sm max-w-2xl">{meta}</p> : null}
    </header>
  );
}

export function TabBar({ children }: { children: ReactNode }) {
  return <div className="flex border-b-2 border-[var(--nq-dim)] mb-8">{children}</div>;
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
    <button 
      type="button" 
      className={`flex-1 py-4 font-black uppercase tracking-widest transition-colors ${active ? "text-[var(--nq-copper)] border-b-4 border-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`} 
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function InlineActions({ children }: { children: ReactNode }) {
  return <div className="flex flex-col sm:flex-row gap-4 mt-6">{children}</div>;
}

/**
 * Khối có tiêu đề — đơn vị chia trang.
 *
 * `count` in số bản ghi ngay cạnh tiêu đề: với danh sách 18 việc treo hay 30 lần
 * sửa, người vận hành cần con số trước khi cuộn. `tourId` gắn `data-tour` để
 * tour hướng dẫn trỏ được vào đúng khối này.
 */
export function OpsCard({
  eyebrow,
  title,
  count,
  countLabel = "bản ghi",
  tourId,
  children,
}: {
  eyebrow?: string;
  title?: string;
  count?: number;
  countLabel?: string;
  tourId?: string;
  children: ReactNode;
}) {
  const head = title ? (
    <div className="flex items-center gap-4 mb-6">
      <h2 className="text-2xl font-black uppercase text-[var(--nq-fg)]">{title}</h2>
      {typeof count === "number" ? (
        <span className="nq-ink-on-solid text-sm bg-[var(--nq-copper)] px-3 py-1 rounded-full">
          {count} {countLabel}
        </span>
      ) : null}
    </div>
  ) : null;
  return (
    <section className="mb-10 w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] md:mb-12 md:p-8" data-tour={tourId}>
      {eyebrow ? <p className="text-[var(--nq-dim)] font-mono text-sm mb-2 uppercase tracking-widest">{eyebrow}</p> : null}
      {head}
      {children}
    </section>
  );
}

export function StepDone({ label, timingMs }: { label: string; timingMs?: number }) {
  return (
    <div className="flex items-center justify-between p-4 bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] text-[var(--nq-dim)]">
      <div className="flex items-center gap-3">
        <span className="text-[var(--nq-green)] font-black text-xl" aria-hidden="true">
          ✓
        </span>
        <span className="font-bold uppercase tracking-widest text-sm">{label}</span>
      </div>
      {timingMs != null ? (
        <span className="font-mono text-xs">{(timingMs / 1000).toFixed(1)}s</span>
      ) : null}
    </div>
  );
}

export function FixedBottomBar({ children }: { children: ReactNode }) {
  return (
    <div className="fixed bottom-0 left-0 w-full p-4 bg-[var(--nq-bg)]/80 backdrop-blur-md border-t-2 border-[var(--nq-dim)] z-50">
      <div className="max-w-2xl mx-auto flex gap-4">
        {children}
      </div>
    </div>
  );
}

export function StatusChip({
  tone = "default",
  children,
}: {
  tone?: "default" | "warn" | "ok" | "danger";
  children: ReactNode;
}) {
  const bg =
    tone === "warn"
      ? "nq-ink-on-solid bg-[var(--nq-warn)]"
      : tone === "ok"
        ? "nq-ink-on-solid bg-[var(--nq-green)]"
        : tone === "danger"
          ? "nq-ink-on-solid bg-[var(--nq-red)]"
          : "bg-[var(--nq-surface-hi)] text-[var(--nq-fg)] border border-[var(--nq-dim)]";
  return (
    <span className={`inline-block px-2 py-1 text-xs font-bold uppercase tracking-widest ${bg}`}>
      {children}
    </span>
  );
}

export function Toolbar({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap gap-4 mb-6">{children}</div>;
}

export function Notice({ children }: { children: ReactNode }) {
  return <p className="text-sm font-mono text-[var(--nq-dim)] border-l-4 border-[var(--nq-copper)] pl-4 my-6">{children}</p>;
}

export function LinkGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">{children}</div>;
}

export function LinkTile({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} className={`bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all group hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[4px_4px_0px_0px_var(--nq-copper-dim)] ${className}`.trim()}>
      <span className="font-bold uppercase tracking-widest text-sm group-hover:text-[var(--nq-copper)] text-[var(--nq-fg)] transition-colors">{children}</span>
    </Link>
  );
}

function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-24 bg-[var(--nq-dim)]/20 rounded w-full" />
      ))}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════
   v3.3 — khối mang thông tin thật
   ══════════════════════════════════════════════════════════════════════════ */

/**
 * Dải tóm tắt đếm được.
 *
 * Đặt ngay dưới đầu trang, trước danh sách. Với 18 việc treo thì "18 việc · 6
 * quá hạn · 6 đang chờ · 6 xong" trả lời xong câu hỏi đầu tiên của người vận
 * hành; không có dải này họ phải cuộn hết rồi tự nhẩm.
 */
export function Summary({
  cells,
  className = "",
}: {
  cells: Array<{ n: ReactNode; k: string; tone?: "default" | "warn" | "ok" | "danger" }>;
  className?: string;
}) {
  return (
    <div className={`flex flex-wrap gap-4 mb-8 w-full ${className}`.trim()}>
      {cells.map((c) => {
        const bg =
          c.tone === "warn"
            ? "nq-ink-on-solid bg-[var(--nq-warn)]"
            : c.tone === "ok"
              ? "nq-ink-on-solid bg-[var(--nq-green)]"
              : c.tone === "danger"
                ? "nq-ink-on-solid bg-[var(--nq-red)]"
                : "bg-[var(--nq-surface-hi)] text-[var(--nq-fg)] border-2 border-[var(--nq-dim)]";
        return (
          <div
            key={c.k}
            data-tone={c.tone ?? "default"}
            className={`nq-summary-cell flex min-w-[140px] flex-1 flex-col p-4 shadow-[4px_4px_0px_0px_var(--nq-copper-dim)] ${bg}`}
          >
            <span className="nq-summary-n mb-1 text-3xl font-black tabular-nums">{c.n}</span>
            <span className="nq-summary-k text-xs font-mono uppercase tracking-widest opacity-80">{c.k}</span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Thanh độ tin cậy của một tin do agent tóm tắt.
 *
 * Vừa thanh vừa số: thanh để so nhanh giữa các dòng, số để người duyệt có căn
 * cứ. Dưới 70% đổi sang màu cảnh báo — đó là ngưỡng nên đọc kỹ trước khi duyệt.
 */
export function Confidence({ value }: { value: unknown }) {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  const pct = Math.max(0, Math.min(100, Math.round(n * 100)));
  const isLow = pct < 70;
  return (
    <span className="flex items-center gap-2" title={`Độ tin cậy: ${pct}%`}>
      <span className="w-16 h-2 bg-[var(--nq-dim)]/20 rounded-full overflow-hidden">
        <span 
          className={`block h-full ${isLow ? "bg-[var(--nq-warn)]" : "bg-[var(--nq-green)]"}`} 
          style={{ width: `${pct}%` }} 
        />
      </span>
      <span className={`font-mono text-xs ${isLow ? "text-[var(--nq-warn)] font-bold" : "text-[var(--nq-dim)]"}`}>{pct}%</span>
    </span>
  );
}

/** Thẻ chọn — mẫu phiếu, mỗi thẻ nói rõ bao nhiêu bước và làm gì. */
export function PickCard({
  steps,
  stepsUnit = "bước",
  name,
  what,
  go,
  disabled,
  onClick,
}: {
  steps: number;
  stepsUnit?: string;
  name: string;
  what: string;
  go: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button 
      type="button" 
      disabled={disabled} 
      onClick={onClick}
      className="w-full text-left bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] transition-all flex flex-col justify-between disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]"
    >
      <div className="mb-6">
        <span className="text-2xl font-black text-[var(--nq-copper)] mb-2 block">
          {steps} <span className="text-sm font-mono uppercase tracking-widest">{stepsUnit}</span>
        </span>
        <span className="text-xl font-bold uppercase text-[var(--nq-fg)] block mb-2">{name}</span>
        <span className="text-sm font-mono text-[var(--nq-dim)] block">{what}</span>
      </div>
      <span className="text-sm font-bold uppercase tracking-widest text-[var(--nq-copper)] border-2 border-[var(--nq-copper)] py-2 text-center hover:bg-[var(--nq-copper)] hover:text-[#0e0c0a] transition-colors">{go}</span>
    </button>
  );
}

/** Bảng số liệu: cột số căn phải, đơn vị thành cột riêng. */
export function DataTable({
  caption,
  head,
  children,
  note,
}: {
  caption: string;
  head: Array<{ label: string; num?: boolean }>;
  children: ReactNode;
  note?: string;
}) {
  return (
    <div className="mb-8">
      <div className="overflow-x-auto bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
        <table className="w-full text-left border-collapse">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)]">
              {head.map((h) => (
                <th key={h.label} scope="col" className={`p-4 font-black uppercase tracking-widest text-[var(--nq-dim)] ${h.num ? "text-right" : ""}`}>
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
      {note ? <p className="text-sm font-mono text-[var(--nq-dim)] mt-4">{note}</p> : null}
    </div>
  );
}

export type ToastItem = { id: number; text: string; kind: "ok" | "err" };

/**
 * Toast xác nhận: tự tắt sau 4 giây, tắt tay được.
 *
 * Vì sao tự viết: một hàng đợi ba dòng không đáng thêm dependency, và bộ đếm
 * phải nằm chung với React state để `clearTimeout` chạy khi component rời khỏi
 * cây — thư viện ngoài cũng chỉ làm đúng thế.
 */
export function useToasts(): {
  toasts: ToastItem[];
  push: (text: string, kind?: "ok" | "err") => void;
  dismiss: (id: number) => void;
} {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<number[]>([]);

  useEffect(
    () => () => {
      timers.current.forEach((t) => window.clearTimeout(t));
    },
    [],
  );

  const dismiss = useCallback((id: number) => {
    setToasts((v) => v.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (text: string, kind: "ok" | "err" = "ok") => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((v) => [...v, { id, text, kind }]);
      timers.current.push(window.setTimeout(() => dismiss(id), 4000));
    },
    [dismiss],
  );

  return { toasts, push, dismiss };
}

export function Toasts({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div
      className="fixed top-20 left-1/2 z-[100] flex w-full max-w-md -translate-x-1/2 flex-col gap-2 px-4 pointer-events-none md:top-24"
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto flex items-start justify-between gap-3 border-2 p-4 shadow-[6px_6px_0_0_rgba(0,0,0,0.35)] ${
            t.kind === "ok"
              ? "nq-ink-on-solid bg-[var(--nq-ok)] border-[var(--nq-ok)]"
              : "nq-ink-on-solid bg-[var(--nq-danger)] border-[var(--nq-danger)]"
          }`}
        >
          <p className="text-sm font-semibold leading-snug tracking-normal normal-case">{t.text}</p>
          <button
            type="button"
            className="shrink-0 opacity-80 hover:opacity-100 transition-opacity min-w-8 min-h-8"
            onClick={() => onDismiss(t.id)}
            aria-label="Tắt thông báo"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
