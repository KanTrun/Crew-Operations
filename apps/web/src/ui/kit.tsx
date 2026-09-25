"use client";

import Link from "next/link";
import { CSSProperties, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useCallback, useEffect, useRef, useState } from "react";
import { API } from "../lib/api";
import { fieldLabel, formatFieldValue } from "../lib/labels";
import { Icon, type IconName } from "./icons";

export const btnPrimary: CSSProperties = {};
export const btnGhost: CSSProperties = {};
export const btnSecondary: CSSProperties = {};
export const btnDanger: CSSProperties = {};
export const inputStyle: CSSProperties = {};
export const inputClassName = "nq-input";
export const selectClassName = "nq-select";
export const textareaClassName = "nq-input nq-textarea";

type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "icon";
type BtnSize = "sm" | "md";

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
function btnClass(variant: BtnVariant, block?: boolean, size: BtnSize = "md") {
  const base = "nq-btn";
  const w = block ? " nq-btn-block" : "";
  const s = size === "sm" ? " nq-btn-sm" : "";
  if (variant === "primary") return `${base} nq-btn-primary nq-ink-on-solid${w}${s}`;
  if (variant === "secondary") return `${base} nq-btn-secondary${w}${s}`;
  if (variant === "danger") return `${base} nq-btn-danger nq-ink-on-solid${w}${s}`;
  if (variant === "icon") return `${base} nq-btn-ghost nq-btn-icon${w}${s}`;
  return `${base} nq-btn-ghost${w}${s}`;
}

export function BtnLink({
  href,
  variant = "primary",
  children,
  block,
  size = "md",
  className = "",
}: {
  href: string;
  variant?: BtnVariant;
  children: ReactNode;
  block?: boolean;
  size?: BtnSize;
  className?: string;
}) {
  return (
    <Link href={href} className={className || btnClass(variant, block, size)}>
      {children}
    </Link>
  );
}

/* Dãy nút hành động của trang.
   Phải có `flex-wrap`: ở bề rộng trung bình (768–1024px) các nút nằm cùng một
   hàng nhưng không đủ chỗ. `.nq-btn` đặt `white-space: nowrap` (đúng — nhãn nút
   không được ngắt dòng), nên khi hàng không đủ chỗ thì khối flex nở ra và đẩy
   tràn cả trang. Cho phép ngắt hàng thì nút rơi xuống dòng dưới, đúng ý người
   dùng hơn là cắt cụt hoặc tràn. Đo được: /hom-nay @768px tràn 4px trước khi sửa. */
export function PageActions({ children }: { children: ReactNode }) {
  return <div className="flex flex-col sm:flex-row sm:flex-wrap gap-4 mt-8">{children}</div>;
}

export function Kicker({ children }: { children: ReactNode }) {
  return <p className="text-sm font-mono text-[var(--nq-accent)] uppercase tracking-widest mb-2">{children}</p>;
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
    <div className={`nq-tech mt-8 ${className}`.trim()}>
      <button
        type="button"
        className="nq-tech__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>{summary}</span>
        <span aria-hidden="true" className="nq-tech__sign">{open ? "−" : "+"}</span>
      </button>
      {open && lines.length > 0 ? (
        <ul className="nq-tech__body">
          {lines.map((line, i) => (
            /* eslint-disable-next-line react/no-array-index-key */
            <li key={`${i}-${line}`}>{line}</li>
          ))}
        </ul>
      ) : null}
      {open && children ? <div className="nq-tech__body">{children}</div> : null}
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

/**
 * Trạng thái RỖNG.
 *
 * Trước đây: viền `border-2 dashed` + bóng cứng — bề mặt "brutalist", lệch hẳn
 * với phần còn lại của hệ, và nét đứt đọc ra như "lỗi" chứ không phải "chưa có
 * gì". Trạng thái rỗng KHÔNG phải lỗi: nó là trạng thái bình thường của một
 * danh sách chưa có dữ liệu, nên phải trông bình tĩnh.
 *
 * Nền ĐẶC theo token surface (không kính): đây là khối nội dung, người dùng
 * cần đọc dòng giải thích trên nó. `children` là CÂU GIẢI THÍCH VIỆC CẦN LÀM,
 * không phải thông báo lỗi — xem quy ước trong docs/design-guidelines.md.
 */
export function Empty({
  children,
  title = "Không có dữ liệu",
  icon,
  action,
}: {
  children: ReactNode;
  title?: string;
  /** Icon tuỳ chọn — TRUYỀN `<Icon/>`, không truyền emoji. */
  icon?: ReactNode;
  /** Lối thoát: nút dẫn tới việc nên làm tiếp. Không có thì chỉ là thông báo. */
  action?: ReactNode;
}) {
  return (
    <div className="nq-empty">
      {icon ? <div className="nq-empty__icon">{icon}</div> : null}
      <h3 className="nq-empty__title">{title}</h3>
      <p className="nq-empty__body">{children}</p>
      {action ? <div className="nq-empty__action">{action}</div> : null}
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
      <div className="flex border-b border-[var(--nq-line)] bg-[var(--nq-surface)] p-4 gap-4">
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
  const label = children ? <span className="block text-sm font-mono text-[var(--nq-accent)] uppercase tracking-widest mb-4">{children}</span> : null;
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
      <div className="h-full bg-[var(--nq-accent)] transition-all duration-500 ease-out" style={{ width: `${pct}%` }} />
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
  size = "md",
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
  size?: BtnSize;
  className?: string;
}) {
  return (
    <button
      type={type}
      disabled={disabled || busy}
      aria-busy={busy ? true : undefined}
      onClick={onClick}
      title={title}
      className={className || btnClass(variant, block, size)}
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
          <span className="nq-ink-on-solid text-sm bg-[var(--nq-accent)] px-3 py-1 rounded-full">
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
      <p className="text-sm font-mono text-[var(--nq-accent)] uppercase tracking-widest mb-2">{kicker}</p>
      {/* Tiêu đề trang dùng font display của hệ, KHÔNG dùng `font-black uppercase
          tracking-tighter`. Kiểu cũ là dấu hiệu nhận dạng của giao diện máy dựng,
          và với tiếng Việt thì hại thật: chữ hoa cỡ lớn cộng khoảng chữ bị siết
          làm dấu mũ/dấu móc chồng lên nhau. Hệ đã có quy ước ở `.nq-gate-title`
          và `.nq-h1` — theo quy ước đó. */}
      <h1 className="nq-page-title mb-4">{title}</h1>
      {meta ? <p className="text-[var(--nq-dim)] font-mono text-sm max-w-2xl">{meta}</p> : null}
    </header>
  );
}

/**
 * Thanh chọn giữa các khung nhìn của CÙNG một trang.
 *
 * Trước đây `TabButton` dùng `border-b-4` + `font-black uppercase tracking-widest`
 * — vạch 4px đè lên biên khối và chữ hoa giãn rộng làm nhãn dài bị gãy dòng ở
 * màn hẹp. Bản này dùng pill trên nền accent nhạt: mục đang chọn đọc ra bằng
 * NỀN, không bằng một vạch dày chiếm chỗ.
 *
 * `count` cho biết số bản ghi trong mỗi khung nhìn — biết trước khi bấm thì
 * không phải mở từng tab để tìm cái có dữ liệu.
 */
/**
 * Nhóm nút chọn chế độ / khung nhìn trong cùng một trang.
 *
 * KHÔNG dùng `role="tablist"` — xem lý do đầy đủ ở `TabButton`: các nút này
 * không điều khiển `tabpanel` nào, nên `role="group"` mô tả đúng hơn (một nhóm
 * nút có quan hệ với nhau). Gán `tablist` mà không có `tab`/`tabpanel` khớp
 * cặp sẽ khiến công cụ hỗ trợ đọc sai cấu trúc trang.
 */
export function TabBar({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <div className="nq-tabbar" role="group" aria-label={label}>
      {children}
    </div>
  );
}

export function TabButton({
  active,
  onClick,
  children,
  count,
  disabled = false,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
  count?: number;
  disabled?: boolean;
}) {
  return (
    /* GIỮ `role` mặc định là BUTTON — KHÔNG đặt `role="tab"`.
       Bản trước của tôi thêm `role="tab"` để "chuẩn ARIA", nhưng đó là SAI và
       gây hồi quy thật: `role="tab"` GHI ĐÈ role button, nên mọi truy vấn
       `getByRole("button", …)` không còn khớp — hai bài e2e đỏ vì lý do này.
       Hơn nữa `role="tab"` chỉ hợp lệ khi có `role="tablist"` bọc ngoài và
       `role="tabpanel"` liên kết bằng `aria-controls`; ở đây các nút chỉ ĐỔI
       CHẾ ĐỘ NHẬP (mic/meet/audio/text) chứ không mở panel tương ứng, nên gán
       role tab là mô tả sai hành vi, tệ hơn là để mặc định.
       Trạng thái đang chọn đã được truyền đạt bằng `aria-selected` + `data-on`
       và bằng NỀN accent, không cần role tab. */
    <button
      type="button"
      aria-selected={active}
      disabled={disabled}
      className="nq-tab"
      data-on={active ? "1" : "0"}
      onClick={onClick}
    >
      {children}
      {typeof count === "number" ? <span className="nq-tab__count">{count}</span> : null}
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
        <span className="nq-ink-on-solid text-sm bg-[var(--nq-accent)] px-3 py-1 rounded-full">
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
    <div className="fixed bottom-0 left-0 w-full p-4 bg-[var(--nq-bg)]/80 backdrop-blur-md border-t border-[var(--nq-line)] z-50">
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
  return <p className="text-sm font-mono text-[var(--nq-dim)] border-l-4 border-[var(--nq-accent)] pl-4 my-6">{children}</p>;
}

export function LinkGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">{children}</div>;
}

export function LinkTile({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} className={`nq-surface-tile p-6 transition-colors group ${className}`.trim()}>
      <span className="font-bold uppercase tracking-widest text-sm group-hover:text-[var(--nq-accent)] text-[var(--nq-fg)] transition-colors">{children}</span>
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
            {/* Nhãn KHÔNG dùng `opacity-80`: ô có tone là ô NỀN ĐẶC (vàng/ngọc/đỏ),
                và giảm opacity trên nền đặc làm chữ tối mờ đi — đo được 1.9:1 trên
                ô vàng. Trước đây nhãn còn kế thừa màu từ ô, nên trên ô tone nó ra
                chữ tối trên nền tối (4.3:1, và 3.0:1 khi đã giảm opacity).
                Nhãn giờ khai màu theo CÙNG họ với nền ô: ô màu nào thì nhãn lấy
                bản `-ink` của họ đó, đủ tương phản ở mọi tone. */}
            <span className="nq-summary-k text-xs font-mono uppercase tracking-widest">{c.k}</span>
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
        <span className="text-2xl font-black text-[var(--nq-accent)] mb-2 block">
          {steps} <span className="text-sm font-mono uppercase tracking-widest">{stepsUnit}</span>
        </span>
        <span className="text-xl font-bold uppercase text-[var(--nq-fg)] block mb-2">{name}</span>
        <span className="text-sm font-mono text-[var(--nq-dim)] block">{what}</span>
      </div>
      <span className="nq-cta nq-cta--ghost nq-cta--sm">{go}</span>
    </button>
  );
}

/** Bảng số liệu — dùng `.nq-table` (đồng bộ kit Table). */
export function DataTable({
  caption,
  head,
  children,
  note,
  compact,
}: {
  caption: string;
  head: Array<{ label: string; num?: boolean }>;
  children: ReactNode;
  note?: string;
  compact?: boolean;
}) {
  return (
    <div className="mb-6">
      <div className="nq-table-wrap">
        <table className={`nq-table${compact ? " nq-table--compact" : ""}`}>
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              {head.map((h) => (
                <th key={h.label} scope="col" data-num={h.num ? "1" : undefined} className={h.num ? "is-right" : undefined}>
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
      {note ? <p className="nq-table-note">{note}</p> : null}
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

// ── Additional UI Components for Gmail Page ──────────────────────────────

export interface TableColumn<T = Record<string, unknown>> {
  key: string;
  header: string;
  width?: number | string;
  render?: (value: any, row: T) => ReactNode;
  align?: "left" | "center" | "right";
}

export function Table<T extends Record<string, any> = Record<string, any>>({
  columns,
  rows,
  emptyMessage = "Không có dữ liệu",
  emptyHint = "",
  className = "",
}: {
  columns: TableColumn<T>[];
  rows: T[];
  emptyMessage?: string;
  emptyHint?: string;
  className?: string;
}) {
  if (rows.length === 0) {
    return <Empty title={emptyMessage}>{emptyHint}</Empty>;
  }

  return (
    <div className={`nq-table-wrap ${className}`.trim()}>
      <table className="nq-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                style={{ width: col.width }}
                className={col.align === "center" ? "is-center" : col.align === "right" ? "is-right" : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{ width: col.width }}
                  className={col.align === "center" ? "is-center" : col.align === "right" ? "is-right" : undefined}
                >
                  {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Nhãn trạng thái nhỏ.
 *
 * Trước đây: `border-2` + `font-bold uppercase tracking-widest` + chữ đen trên
 * nền màu đặc. Với 4 họ màu và 5 "variant", tổ hợp `border-2` + nền sáng đã
 * từng gây lỗi tương phản 1.01:1 ở `nq-surface-tile`.
 *
 * Bản này theo quy ước trạng thái của hệ: NỀN nhạt (`-soft`) + CHỮ dùng bản
 * `-ink`. Nhờ vậy nhãn đọc được ở mọi họ màu mà không phải chọn chữ đen hay
 * trắng tuỳ nền.
 */
export function Badge({
  children,
  variant = "outline",
  size = "md",
  className = "",
}: {
  children: ReactNode;
  variant?: "primary" | "success" | "warning" | "danger" | "outline";
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
}) {
  return (
    <span
      className={`nq-badge nq-badge--${variant} nq-badge--${size} ${className}`.trim()}
    >
      {children}
    </span>
  );
}

/**
 * Chú thích khi trỏ chuột.
 *
 * Trước đây chỉ nghe `onMouseEnter`/`onMouseLeave` — bàn phím và màn hình cảm
 * ứng không có cách nào mở được, nên nội dung chú thích mất hẳn với hai nhóm
 * người dùng đó. Bản này mở được bằng tiêu điểm bàn phím (`:focus-within`) và
 * bằng chạm, dùng kính theo Phase 4 vì đây là lớp nổi trên nội dung.
 *
 * `content` phải là chữ NGẮN: chú thích không phải chỗ giải thích dài.
 */
export function Tooltip({
  children,
  content,
  position = "top",
}: {
  children: ReactNode;
  content: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
}) {
  const [visible, setVisible] = useState(false);
  return (
    <span
      className="nq-tip-wrap"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span className={`nq-tip nq-tip--${position}`} role="tooltip">
          {content}
        </span>
      )}
    </span>
  );
}

/**
 * Lớp phủ chờ, chặn tương tác cho tới khi xong.
 *
 * Dùng kính bậc 3 (`--nq-glass-3`): đây là lớp chắn hẳn nội dung phía sau, nên
 * phải đục nhất trong ba bậc — vừa để chữ trên nó đọc được, vừa để người dùng
 * hiểu là nội dung bên dưới tạm thời không dùng được.
 *
 * `role="status"` + `aria-live` để công cụ hỗ trợ đọc thông báo; trước đây khối
 * này chỉ là hình, người dùng trình đọc màn hình không biết trang đang bận.
 */
export function LoadingOverlay({
  className = "",
  message = "Đang tải...",
}: {
  className?: string;
  message?: string;
}) {
  return (
    <div className={`nq-loading-overlay ${className}`.trim()}>
      <div className="nq-loading-overlay__panel" role="status" aria-live="polite">
        <Spinner />
        <p className="nq-loading-overlay__text">{message}</p>
      </div>
    </div>
  );
}

/**
 * Tab dạng mảng `{id,label}` — cùng hệ với `TabBar` nhưng nhận dữ liệu thay vì
 * children. Trước đây dùng `border-b-2` + `font-black uppercase tracking-widest`:
 * vạch 2px đè lên biên khối, và chữ hoa giãn rộng làm nhãn dài gãy dòng ở màn
 * hẹp. Đưa về cùng `.nq-tab` để hai lối gọi tab trong hệ trông y hệt nhau.
 */
export function Tabs({
  value,
  onChange,
  tabs,
  className = "",
}: {
  value: string;
  onChange: (value: string) => void;
  tabs: { id: string; label: string; icon?: IconName; disabled?: boolean }[];
  className?: string;
}) {
  return (
    /* Không dùng `role="tablist"`/`role="tab"` — xem lý do ở `TabButton`:
       role tab GHI ĐÈ role button và làm hỏng truy vấn `getByRole("button")`.
       Ở đây cũng không có `aria-controls` trỏ tới panel nào, nên gán role tab
       là mô tả sai. `aria-pressed` mới đúng: đây là các nút BẬT/TẮT một lựa
       chọn, không phải tab điều khiển panel. */
    <div className={`nq-tabbar ${className}`.trim()}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          aria-pressed={value === tab.id}
          disabled={tab.disabled}
          className="nq-tab"
          data-on={value === tab.id ? "1" : "0"}
          onClick={() => !tab.disabled && onChange(tab.id)}
        >
          {tab.icon ? <Icon name={tab.icon} size={16} /> : null}
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}

export function TabPanel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`mt-6 ${className}`}>{children}</div>;
}

/** Skeleton công khai — shimmer khi chờ dữ liệu. */
export function Skeleton({ rows = 3, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`nq-skeleton-wrap ${className}`.trim()} aria-busy="true" aria-label="Đang tải">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={`nq-skeleton nq-skeleton-line${i === 0 ? "" : i % 2 ? " nq-skeleton-line-sm" : ""}`} />
      ))}
    </div>
  );
}

export type DataListItem = { label: string; value: ReactNode };

/** Cặp nhãn/giá trị doanh nghiệp — thay JSON.stringify trên UI. */
export function DataList({
  items,
  data,
  keys,
  className = "",
  nested,
}: {
  items?: DataListItem[];
  data?: Record<string, unknown>;
  keys?: string[];
  className?: string;
  nested?: boolean;
}) {
  let rows: DataListItem[] = items ?? [];
  if (!items && data) {
    const ks = keys ?? Object.keys(data);
    rows = ks.map((k) => {
      const v = data[k];
      if (nested && v && typeof v === "object" && !Array.isArray(v)) {
        return {
          label: fieldLabel(k),
          value: <DataList data={v as Record<string, unknown>} nested />,
        };
      }
      return { label: fieldLabel(k), value: formatFieldValue(v) };
    });
  }

  if (rows.length === 0) {
    return <Empty title="Không có chi tiết">Chưa có trường nào để hiển thị.</Empty>;
  }

  return (
    <dl className={`nq-datalist ${className}`.trim()}>
      {rows.map((row, i) => (
        <div key={`${row.label}-${i}`} className="nq-datalist__row">
          <dt className="nq-datalist__label">{row.label}</dt>
          <dd className="nq-datalist__value">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Dialog chung — portal overlay, Escape đóng, z-index token. */
export function Dialog({
  open,
  title,
  children,
  onClose,
  footer,
  busy,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  busy?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open || typeof document === "undefined") return null;

  return (
    <div className="nq-dialog-overlay" onClick={busy ? undefined : onClose} role="presentation">
      <div
        className="nq-dialog-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nq-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="nq-dialog-head">
          <h2 id="nq-dialog-title" className="nq-dialog-title">
            {title}
          </h2>
          <button type="button" className="nq-btn nq-btn-ghost nq-btn-icon nq-btn-sm" onClick={onClose} disabled={busy} aria-label="Đóng">
            ×
          </button>
        </header>
        <div className="nq-dialog-body">{children}</div>
        {footer ? <div className="nq-dialog-footer">{footer}</div> : null}
      </div>
    </div>
  );
}

/** Drawer phải — chi tiết kỹ thuật / panel phụ. */
export function Drawer({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="nq-drawer-overlay" onClick={onClose} role="presentation">
      <aside
        className="nq-drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nq-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="nq-drawer-head">
          <h2 id="nq-drawer-title" className="nq-drawer-title">
            {title}
          </h2>
          <button type="button" className="nq-btn nq-btn-ghost nq-btn-icon nq-btn-sm" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        </header>
        <div className="nq-drawer-body">{children}</div>
      </aside>
    </div>
  );
}
