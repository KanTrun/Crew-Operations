"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import { matHangLabel, treoLabel } from "../../lib/present";

type TonRow = { hang?: string; so_luong?: number; don_vi?: string; duoi_nguong?: boolean };
type TreoBreakdown = { trang_thai: string; so_luong: number };
type SuaPreview = { loai?: string; luc?: string; ai?: string };

const TON_COLORS = { ok: "var(--nq-ok)", warn: "var(--nq-warn)" };
const TREO_COLORS = ["#c4a574", "#d4a017", "#6f9b7a", "#d45d4a", "#8b7355", "#5c7a8a"];

function chartMotion(reduced: boolean) {
  return reduced
    ? { className: "" }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.48, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
      };
}

export function TonBarChart({ rows }: { rows: TonRow[] }) {
  const reduced = useReducedMotion() ?? false;
  const [hovered, setHovered] = useState<number | null>(null);
  const data = rows.filter((r) => r.hang).slice(0, 8);
  const max = Math.max(1, ...data.map((r) => Number(r.so_luong) || 0));

  if (data.length === 0) {
    return (
      <motion.div className="nq-dash-chart" {...chartMotion(reduced)}>
        <h3 className="nq-dash-chart-title">Tồn kho hôm nay</h3>
        <p className="nq-dash-chart-empty">Chưa có dữ liệu tồn trong sổ tiêu thụ.</p>
      </motion.div>
    );
  }

  return (
    <motion.div className="nq-dash-chart nq-dash-chart--interactive" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Tồn kho hôm nay</h3>
      <p className="nq-dash-chart-hint">Di chuột từng hàng để xem chi tiết</p>
      <ul className="nq-dash-bars" role="list">
        {data.map((row, i) => {
          const qty = Number(row.so_luong) || 0;
          const pct = Math.round((qty / max) * 100);
          const warn = Boolean(row.duoi_nguong);
          const ten = matHangLabel(row.hang);
          const donVi = row.don_vi || "đơn vị";
          const active = hovered === i;
          return (
            <li
              key={`${row.hang}-${i}`}
              className={`nq-dash-bar-row${active ? " nq-dash-bar-row--active" : ""}${warn ? " nq-dash-bar-row--warn" : ""}`}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(i)}
              onBlur={() => setHovered(null)}
              tabIndex={0}
            >
              <span className="nq-dash-bar-label">{ten}</span>
              <div className="nq-dash-bar-track">
                <motion.span
                  className="nq-dash-bar-fill"
                  style={{ background: warn ? TON_COLORS.warn : TON_COLORS.ok }}
                  initial={reduced ? { width: `${pct}%` } : { width: 0 }}
                  animate={{ width: `${pct}%`, opacity: active ? 1 : 0.85 }}
                  transition={{ duration: 0.6, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
              <span className="nq-dash-bar-val" title={`${qty} ${donVi}`}>
                {qty} <span className="nq-dash-bar-unit">{donVi}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </motion.div>
  );
}

export function TreoDonutChart({ breakdown, total }: { breakdown: TreoBreakdown[]; total: number }) {
  const reduced = useReducedMotion() ?? false;
  const [activeStatus, setActiveStatus] = useState<string | null>(null);
  const slices = breakdown.filter((b) => b.so_luong > 0);
  const sum = slices.reduce((a, b) => a + b.so_luong, 0) || total || 1;
  let angle = -90;
  const r = 42;
  const cx = 52;
  const cy = 52;

  const arcs = slices.map((row, i) => {
    const n = row.so_luong;
    const sweep = (n / sum) * 360;
    const start = angle;
    angle += sweep;
    const rad = (deg: number) => (deg * Math.PI) / 180;
    const x1 = cx + r * Math.cos(rad(start));
    const y1 = cy + r * Math.sin(rad(start));
    const x2 = cx + r * Math.cos(rad(start + sweep));
    const y2 = cy + r * Math.sin(rad(start + sweep));
    const large = sweep > 180 ? 1 : 0;
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
    return { status: row.trang_thai, n, d, color: TREO_COLORS[i % TREO_COLORS.length] };
  });

  return (
    <motion.div className="nq-dash-chart nq-dash-chart--interactive" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Việc treo theo trạng thái</h3>
      <p className="nq-dash-chart-hint">Bấm từng mục để làm nổi bật</p>
      <div className="nq-dash-donut-wrap">
        <svg viewBox="0 0 104 104" className="nq-dash-donut" role="img" aria-label={`${total} việc treo`}>
          {arcs.length > 0 ? (
            arcs.map((a) => {
              const dim = activeStatus && activeStatus !== a.status;
              return (
                <motion.path
                  key={a.status}
                  d={a.d}
                  fill={a.color}
                  opacity={dim ? 0.35 : 1}
                  initial={reduced ? { opacity: dim ? 0.35 : 1 } : { opacity: 0, scale: 0.92 }}
                  animate={{ opacity: dim ? 0.35 : 1, scale: activeStatus === a.status ? 1.04 : 1 }}
                  transition={{ duration: 0.35 }}
                  style={{ transformOrigin: `${cx}px ${cy}px`, cursor: "pointer" }}
                  onMouseEnter={() => setActiveStatus(a.status)}
                  onMouseLeave={() => setActiveStatus(null)}
                  onClick={() => setActiveStatus((s) => (s === a.status ? null : a.status))}
                />
              );
            })
          ) : (
            <circle cx={cx} cy={cy} r={r} fill="var(--nq-surface)" stroke="var(--nq-line)" />
          )}
          <circle cx={cx} cy={cy} r={26} fill="var(--nq-bg-elevated)" />
          <text x={cx} y={cy - 2} textAnchor="middle" className="nq-dash-donut-center">
            {total}
          </text>
          <text x={cx} y={cy + 12} textAnchor="middle" className="nq-dash-donut-sub">
            việc
          </text>
        </svg>
        <ul className="nq-dash-legend" role="list">
          {arcs.map((a) => (
            <li key={a.status}>
              <button
                type="button"
                className={`nq-dash-legend-btn${activeStatus === a.status ? " nq-dash-legend-btn--active" : ""}`}
                onMouseEnter={() => setActiveStatus(a.status)}
                onMouseLeave={() => setActiveStatus(null)}
                onClick={() => setActiveStatus((s) => (s === a.status ? null : a.status))}
              >
                <span className="nq-dash-legend-swatch" style={{ background: a.color }} />
                {treoLabel(a.status)} <span className="nq-dash-legend-n">({a.n})</span>
              </button>
            </li>
          ))}
          {arcs.length === 0 ? <li className="nq-muted">Chưa có việc treo</li> : null}
        </ul>
      </div>
    </motion.div>
  );
}

export function SuaTimeline({ items, formatLuc, ghiNhanLabel, actorLabel }: {
  items: SuaPreview[];
  formatLuc: (luc?: string) => string;
  ghiNhanLabel: (loai?: string) => string;
  actorLabel: (ai?: string) => string;
}) {
  const reduced = useReducedMotion() ?? false;
  if (items.length === 0) return null;

  return (
    <motion.section className="nq-dash-timeline nq-dash-chart" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Sửa lịch gần đây</h3>
      <ol className="nq-dash-timeline-list">
        {items.map((g, i) => (
          <motion.li
            key={`${g.luc}-${i}`}
            className="nq-dash-timeline-item"
            initial={reduced ? {} : { opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06, duration: 0.35 }}
            whileHover={reduced ? {} : { x: 4 }}
          >
            <span className="nq-dash-timeline-dot" aria-hidden />
            <div>
              <p className="nq-dash-timeline-title">{ghiNhanLabel(g.loai)}</p>
              <p className="nq-dash-timeline-sub">
                {actorLabel(g.ai)} · {formatLuc(g.luc)}
              </p>
            </div>
          </motion.li>
        ))}
      </ol>
    </motion.section>
  );
}
