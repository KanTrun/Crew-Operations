"use client";

import Link from "next/link";
import { CSSProperties, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useCallback, useEffect, useRef, useState } from "react";
import { API } from "../lib/api";

export const btnPrimary: CSSProperties = {};
export const btnGhost: CSSProperties = {};
export const btnSecondary: CSSProperties = {};
export const btnDanger: CSSProperties = {};
export const inputStyle: CSSProperties = {};
export const inputClassName = "nq-input";
export const selectClassName = "nq-select";
export const textareaClassName = "nq-input nq-textarea";

type BtnVariant = "primary" | "ghost" | "danger";

/**
 * Lớp nút dùng chung — toàn bộ nút trong app đi qua đây.
 *
 * Vì sao phải viết lại: bản cũ dựng nút bằng Tailwind trần —
 * `border-2` không bo góc, cộng bóng cứng `8px 8px 0 0` và dịch chuyển -2px khi
 * hover (kiểu brutalist). Đo trên bản render: 73/79 phần tử có bề mặt trên mặt
 * tiền là hình vuông góc cạnh, và mọi nút trong app đều mang cùng kiểu bóng
 * cứng đó. Đó chính là cảm giác "toàn khung vuông như máy dựng": một khối
 * vuông, một bóng lệch cứng, lặp lại ở mọi nút.
 *
 * Nay nút dùng hệ hình dạng của thiết kế: bo tròn hoàn toàn (pill), bóng mềm
 * theo bậc nổi, lún nhẹ khi bấm, và độ nổi tăng khi hover — đúng ngôn ngữ
 * chuyển động đã khai trong `globals.css`. Chữ giữ nguyên chữ hoa + giãn chữ vì
 * đó là nét nhận diện của quán, không phải lỗi.
 */
function btnClass(variant: BtnVariant, block?: boolean) {
  const base = "nq-btn";
  const w = block ? " nq-btn-block" : "";
  if (variant === "primary") return `${base} nq-btn-primary${w}`;
  if (variant === "danger") return `${base} nq-btn-danger${w}`;
  return `${base} nq-btn-ghost${w}`;
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
    <section className="nq-editorial p-6 md:p-10 mb-10 md:mb-12 w-full" aria-label="Tình trạng">
      <div className="w-full max-w-none">
        <p className="nq-editorial__wordmark">{wordmark}</p>
        <p className="nq-editorial__status">{status}</p>
        {meta ? <p className="nq-editorial__meta">{meta}</p> : null}
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
  // Bậc nổi phân biệt THÔNG TIN: ô cảnh báo/lỗi (warn/ok) là nền đặc vì nó
  // đang báo có chuyện; ô thường chỉ là bề mặt elev-2. Bản cũ dùng `border-2`
  // vuông cộng bóng lệch cứng cho cả hai, nên ô "bình thường" và ô "có cảnh
  // báo" chỉ khác màu chữ — mắt không thấy mức độ khác nhau.
  const bg =
    accent === "warn"
      ? "nq-ink-on-solid bg-[var(--nq-st-warn)]"
      : accent === "ok"
        ? "nq-ink-on-solid bg-[var(--nq-st-ok)]"
        : "bg-[var(--nq-surface-hi)] text-[var(--nq-fg)]";

  const span = large
    ? "nq-bento-tile nq-bento-tile--lg col-span-12 sm:col-span-6 lg:col-span-8 lg:row-span-2 min-h-[200px]"
    : "nq-bento-tile col-span-12 sm:col-span-6 lg:col-span-4 min-h-[140px]";
  const cls = `${span} nq-bento-surface flex flex-col justify-between p-6 ${bg}`;

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
    <div className="nq-surface-row">
      <span className="font-mono text-2xl tracking-widest text-[var(--nq-fg)]" aria-label={`${label} đã được che`}>
        {masked}
      </span>
      <button
        type="button"
        onClick={copy}
        className="ml-auto nq-filter-clear"
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
            <div key={i} className="nq-surface-row nq-surface-row--between">
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
        <div key={i} className="nq-surface-block p-6">
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
    <div className="nq-skeleton nq-skeleton--block w-full" aria-hidden="true">
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

/**
 * Màn hình chặn khi chưa có phiên.
 *
 * Đây là bề mặt có lưu lượng cao nhất trong nhóm "không đăng nhập" — mọi route
 * vận hành đều rơi vào đây khi phiên hết hạn, mà phiên chỉ sống trong
 * sessionStorage nên hết hạn là chuyện thường ngày. Bản cũ dựng bằng Tailwind
 * trần: chữ hoa cỡ 3xl, hai nút vuông `border-2` có bóng cứng 8px — vuông góc,
 * lệch hẳn với phần còn lại của hệ, và trông như một trang khác của sản phẩm
 * khác. Nay dùng đúng thang chữ và hệ nút chung.
 */
export function AuthGate() {
  return (
    <div className="nq-gate">
      <h1 className="nq-gate-title">Cần phiên làm việc</h1>
      <p className="nq-gate-lead">
        Trang này đọc dữ liệu quán qua phiên của bạn. Đăng nhập để tiếp tục.
      </p>
      <div className="nq-gate-actions">
        <BtnLink href="/login" variant="primary">
          Đăng nhập
        </BtnLink>
        <BtnLink href="/dang-ky" variant="ghost">
          Tạo tài khoản
        </BtnLink>
      </div>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="nq-field block mb-4">
      <span className="block text-sm font-bold uppercase tracking-widest text-[var(--nq-dim)] mb-2">{label}</span>
      {hint ? <span className="mb-2 block text-xs leading-relaxed text-[var(--nq-ink-muted)]">{hint}</span> : null}
      {children}
    </label>
  );
}

function joinClasses(...parts: Array<string | undefined | false>) {
  return parts.filter(Boolean).join(" ");
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { className?: string }) {
  return <input className={joinClasses(inputClassName, className)} {...props} />;
}

export function Textarea({
  className,
  rows = 5,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { className?: string }) {
  return <textarea className={joinClasses(textareaClassName, className)} rows={rows} {...props} />;
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { className?: string; children: ReactNode }) {
  return (
    <select className={joinClasses(selectClassName, className)} {...props}>
      {children}
    </select>
  );
}

export function ProgressBar({ value, max, className = "" }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className={`nq-progress w-full ${className}`.trim()} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className="h-full bg-[var(--nq-copper)] transition-all duration-500 ease-out" style={{ width: `${pct}%` }} />
    </div>
  );
}

export const textareaStyle: CSSProperties = {};

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
          : "nq-surface-row text-[var(--nq-fg)]";
  return (
    <li className={`nq-surface-tile flex flex-col p-4 ${bg}`}>
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
    <li className="nq-record">
      <div className="nq-record__head">
        <p className="nq-record__title">{title}</p>
        {sub ? <p className="nq-record__meta">{sub}</p> : null}
      </div>
      {side || actions ? (
        <div className="nq-record__foot">
          {side ? <div className="nq-record__tags">{side}</div> : null}
          {actions ? <div className="nq-record__actions">{actions}</div> : null}
        </div>
      ) : null}
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
    <div className="nq-surface-block p-6 md:p-8 mt-12">
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
    <section className="nq-surface-block mb-10 w-full p-6 md:mb-12 md:p-8" data-tour={tourId}>
      {eyebrow ? <p className="nq-eyebrow text-[var(--nq-dim)]">{eyebrow}</p> : null}
      {head}
      {children}
    </section>
  );
}

export function StepDone({ label, timingMs }: { label: string; timingMs?: number }) {
  return (
    <div className="nq-surface-row nq-surface-row--between text-[var(--nq-dim)]">
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

/**
 * Chip trạng thái — bốn tone lấy từ `--nq-st-*` (xem `globals.css`).
 *
 * Trước đây component này dựng chip bằng Tailwind nền đặc (`bg-[var(--nq-warn)]`
 * + chữ tối), trong khi CSS `.nq-chip--warn` dựng chip bằng viền + chữ màu. Hai
 * dạng cho cùng một trạng thái nên "Quá hạn" trông nặng hơn "Thiếu người" dù
 * hai bên ngang cấp. Nay cả hai đi qua `.nq-chip`, phân biệt bằng modifier.
 */
export function StatusChip({
  tone = "default",
  children,
}: {
  tone?: "default" | "warn" | "ok" | "danger" | "info";
  children: ReactNode;
}) {
  const mod =
    tone === "default"
      ? ""
      : tone === "warn"
        ? " nq-chip--warn"
        : tone === "ok"
          ? " nq-chip--ok"
          : tone === "danger"
            ? " nq-chip--danger"
            : " nq-chip--info";
  return <span className={`nq-chip${mod}`}>{children}</span>;
}

/**
 * Nhãn "Dữ liệu mẫu" — chỉ hiện khi khu vực có bản ghi sinh từ bộ fixture demo.
 * `title` thành tooltip: nói nguồn và cách dọn (`seed_professional_fixture.py --reset`).
 */
export function FixtureChip() {
  return (
    <span
      title="Sinh từ bộ fixture demo — chạy `python scripts/seed_professional_fixture.py --reset` để dọn"
      className="inline-block"
    >
      <StatusChip tone="warn">Dữ liệu mẫu</StatusChip>
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
    <Link href={href} className={`nq-surface-tile p-6 transition-colors group ${className}`.trim()}>
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
                : "nq-surface-row text-[var(--nq-fg)]";
        return (
          <div
            key={c.k}
            data-tone={c.tone ?? "default"}
            className={`nq-summary-cell nq-surface-tile flex min-w-[140px] flex-1 flex-col p-4 ${bg}`}
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
      className="nq-surface-tile flex w-full flex-col justify-between p-6 text-left disabled:opacity-50"
    >
      <div className="mb-6">
        <span className="text-2xl font-black text-[var(--nq-copper)] mb-2 block">
          {steps} <span className="text-sm font-mono uppercase tracking-widest">{stepsUnit}</span>
        </span>
        <span className="text-xl font-bold uppercase text-[var(--nq-fg)] block mb-2">{name}</span>
        <span className="text-sm font-mono text-[var(--nq-dim)] block">{what}</span>
      </div>
      <span className="nq-cta nq-cta--ghost nq-cta--sm">{go}</span>
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
      <div className="nq-surface-frame overflow-x-auto">
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

/** Hộp thoại xác nhận — thay `window.confirm` cho hành động quan trọng. */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel = "Hủy",
  variant = "primary",
  busy,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  variant?: BtnVariant;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div className="nq-confirm-overlay" onClick={busy ? undefined : onCancel}>
      <div
        className="nq-confirm-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nq-confirm-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="nq-confirm-title" className="nq-confirm-title">
          {title}
        </h2>
        <div className="nq-confirm-body">{body}</div>
        <div className="nq-confirm-actions">
          <Btn variant="ghost" onClick={onCancel} disabled={busy} className="nq-btn-compact">
            {cancelLabel}
          </Btn>
          <Btn variant={variant} busy={busy} onClick={onConfirm} className="nq-btn-compact">
            {confirmLabel}
          </Btn>
        </div>
      </div>
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
      className="nq-toasts"
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          data-tone={t.kind === "ok" ? "ok" : "danger"}
          className="nq-toast"
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
