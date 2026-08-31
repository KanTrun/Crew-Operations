"use client";

import { motion, useReducedMotion } from "framer-motion";
import { treoLabel } from "../../lib/present";

type TonRow = { hang?: string; so_luong?: number; duoi_nguong?: boolean };
type TreoPreview = { trang_thai?: string };
type SuaPreview = { loai?: string; luc?: string; ai?: string };

const TON_COLORS = { ok: "var(--nq-ok)", warn: "var(--nq-warn)" };
const TREO_COLORS = ["#c4a574", "#d4a017", "#6f9b7a", "#d45d4a", "#8b7355"];

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
  const data = rows.filter((r) => r.hang).slice(0, 8);
  const max = Math.max(1, ...data.map((r) => Number(r.so_luong) || 0));

  if (data.length === 0) {
    return <p className="nq-dash-chart-empty">Chưa có dữ liệu tồn trong sổ tiêu thụ.</p>;
  }

  return (
    <motion.div className="nq-dash-chart" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Tồn kho</h3>
      <ul className="nq-dash-bars" role="list">
        {data.map((row, i) => {
          const qty = Number(row.so_luong) || 0;
          const pct = Math.round((qty / max) * 100);
          const warn = Boolean(row.duoi_nguong);
          return (
            <li key={`${row.hang}-${i}`} className="nq-dash-bar-row">
              <span className="nq-dash-bar-label" title={row.hang}>
                {row.hang}
              </span>
              <div className="nq-dash-bar-track">
                <motion.span
                  className="nq-dash-bar-fill"
                  style={{ background: warn ? TON_COLORS.warn : TON_COLORS.ok }}
                  initial={reduced ? { width: `${pct}%` } : { width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.6, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
              <span className="nq-dash-bar-val">{qty}</span>
            </li>
          );
        })}
      </ul>
    </motion.div>
  );
}

export function TreoDonutChart({ items, total }: { items: TreoPreview[]; total: number }) {
  const reduced = useReducedMotion() ?? false;
  const counts = new Map<string, number>();
  for (const it of items) {
    const k = it.trang_thai || "dang_cho";
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  const slices = [...counts.entries()];
  const sum = slices.reduce((a, [, n]) => a + n, 0) || 1;
  let angle = -90;
  const r = 42;
  const cx = 52;
  const cy = 52;

  const arcs = slices.map(([status, n], i) => {
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
    return { status, n, d, color: TREO_COLORS[i % TREO_COLORS.length] };
  });

  return (
    <motion.div className="nq-dash-chart" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Việc treo theo trạng thái</h3>
      <div className="nq-dash-donut-wrap">
        <svg viewBox="0 0 104 104" className="nq-dash-donut" role="img" aria-label={`${total} việc treo`}>
          {arcs.length > 0 ? (
            arcs.map((a) => (
              <motion.path
                key={a.status}
                d={a.d}
                fill={a.color}
                initial={reduced ? { opacity: 1 } : { opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.45 }}
                style={{ transformOrigin: `${cx}px ${cy}px` }}
              />
            ))
          ) : (
            <circle cx={cx} cy={cy} r={r} fill="var(--nq-surface)" stroke="var(--nq-line)" />
          )}
          <circle cx={cx} cy={cy} r={26} fill="var(--nq-bg-elevated)" />
          <text x={cx} y={cy + 4} textAnchor="middle" className="nq-dash-donut-center">
            {total}
          </text>
        </svg>
        <ul className="nq-dash-legend" role="list">
          {arcs.map((a) => (
            <li key={a.status}>
              <span className="nq-dash-legend-swatch" style={{ background: a.color }} />
              {treoLabel(a.status)} <span className="nq-dash-legend-n">({a.n})</span>
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
    <motion.section className="nq-dash-timeline" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Sửa lịch gần đây</h3>
      <ol className="nq-dash-timeline-list">
        {items.map((g, i) => (
          <motion.li
            key={`${g.luc}-${i}`}
            initial={reduced ? {} : { opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06, duration: 0.35 }}
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
