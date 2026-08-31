"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import type { RoleSlice } from "../../lib/team-stats";

function chartMotion(reduced: boolean) {
  return reduced
    ? { className: "" }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
      };
}

export function RoleDonutChart({ slices, total }: { slices: RoleSlice[]; total: number }) {
  const reduced = useReducedMotion() ?? false;
  const [activeRole, setActiveRole] = useState<string | null>(null);
  const sum = slices.reduce((a, b) => a + b.n, 0) || total || 1;
  let angle = -90;
  const r = 42;
  const cx = 52;
  const cy = 52;

  const arcs = slices.map((row) => {
    const sweep = (row.n / sum) * 360;
    const start = angle;
    angle += sweep;
    const rad = (deg: number) => (deg * Math.PI) / 180;
    const x1 = cx + r * Math.cos(rad(start));
    const y1 = cy + r * Math.sin(rad(start));
    const x2 = cx + r * Math.cos(rad(start + sweep));
    const y2 = cy + r * Math.sin(rad(start + sweep));
    const large = sweep > 180 ? 1 : 0;
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
    return { ...row, d };
  });

  return (
    <motion.div className="nq-dash-chart nq-dash-chart--interactive" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Phân bố vai trò</h3>
      <p className="nq-dash-chart-hint">Bấm từng mục để làm nổi bật</p>
      <div className="nq-dash-donut-wrap">
        <svg viewBox="0 0 104 104" className="nq-dash-donut" role="img" aria-label={`${total} tài khoản`}>
          {arcs.length > 0 ? (
            arcs.map((a) => {
              const dim = activeRole && activeRole !== a.role;
              return (
                <motion.path
                  key={a.role}
                  d={a.d}
                  fill={a.color}
                  opacity={dim ? 0.35 : 1}
                  initial={reduced ? { opacity: dim ? 0.35 : 1 } : { opacity: 0, scale: 0.92 }}
                  animate={{ opacity: dim ? 0.35 : 1, scale: activeRole === a.role ? 1.04 : 1 }}
                  transition={{ duration: 0.35 }}
                  style={{ transformOrigin: `${cx}px ${cy}px`, cursor: "pointer" }}
                  onMouseEnter={() => setActiveRole(a.role)}
                  onMouseLeave={() => setActiveRole(null)}
                  onClick={() => setActiveRole((s) => (s === a.role ? null : a.role))}
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
            người
          </text>
        </svg>
        <ul className="nq-dash-legend" role="list">
          {arcs.map((a) => (
            <li key={a.role}>
              <button
                type="button"
                className={`nq-dash-legend-btn${activeRole === a.role ? " nq-dash-legend-btn--active" : ""}`}
                onMouseEnter={() => setActiveRole(a.role)}
                onMouseLeave={() => setActiveRole(null)}
                onClick={() => setActiveRole((s) => (s === a.role ? null : a.role))}
              >
                <span className="nq-dash-legend-swatch" style={{ background: a.color }} />
                {a.label} <span className="nq-dash-legend-n">({a.n})</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}
