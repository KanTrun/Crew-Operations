"use client";

/** SpatialMap 2D fallback — isometric/2D anchor map, identical anchor IDs. */

import type { ReactNode } from "react";

export interface Anchor2D {
  anchor_id: string;
  khu_vuc: string;
  label: string;
  x: number;
  y: number;
  kind: string;
}

interface Props {
  anchors: Anchor2D[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  renderBadge?: (anchor: Anchor2D) => ReactNode;
}

export default function SpatialMap2dFallback({
  anchors,
  selectedId,
  onSelect,
  renderBadge,
}: Props) {
  // Scale 100px/unit — map isometric nhẹ (hình thoi).
  const W = 1000;
  const H = 900;
  const cx = W / 2;
  const cy = H / 2;

  return (
    <div className="nq-map2d" role="group" aria-label="Bản đồ không gian quán (2D)">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height="auto"
        aria-hidden="true"
        className="nq-map2d__svg"
      >
        {/* floor */}
        <path
          d={`M ${cx} 40 L ${cx + 400} ${cy - 40} L ${cx} ${H - 60} L ${cx - 400} ${cy - 40} Z`}
          fill="var(--nq-surface-hi)"
          stroke="var(--nq-dim)"
          strokeWidth="2"
        />
        {anchors.map((a) => {
          // iso projection
          const px = cx + (a.x - 5) * 60 - (a.y - 5) * 30;
          const py = cy + (a.x - 5) * 30 + (a.y - 5) * 60 - 800;
          const selected = a.anchor_id === selectedId;
          return (
            <g
              key={a.anchor_id}
              transform={`translate(${px} ${py})`}
              onClick={() => onSelect(a.anchor_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(a.anchor_id);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={a.label}
              className={`nq-map2d__anchor${selected ? " is-selected" : ""}`}
            >
              <circle r="26" fill={selected ? "var(--nq-copper)" : "var(--nq-surface-hi)"} stroke="var(--nq-copper)" strokeWidth="2" />
              <text y="0" textAnchor="middle" dominantBaseline="central" fill="currentColor">
                {a.kind === "thiet_bi" ? "⚙" : "▭"}
              </text>
              <text y="44" textAnchor="middle" className="nq-map2d__label">
                {a.label}
              </text>
              {renderBadge ? <g>{renderBadge(a)}</g> : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
}