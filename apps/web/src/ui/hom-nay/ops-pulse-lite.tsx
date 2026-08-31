"use client";

import Link from "next/link";
import type { OpsPulseModel } from "../../lib/ops-pulse";
import { severityColor } from "../../lib/ops-pulse";

/** Bản 2D — mobile + reduced-motion; cùng semantics với 3D. */
export function OpsPulseLite({ model }: { model: OpsPulseModel }) {
  const color = severityColor(model.severity);
  const pct = Math.round(model.pressure * 100);
  const r = 36;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;

  return (
    <Link href={model.href} className="nq-ops-pulse nq-ops-pulse--lite" aria-label={model.ariaLabel}>
      <div className="nq-ops-pulse__viz" aria-hidden>
        <svg viewBox="0 0 88 88" className="nq-ops-pulse__svg">
          <circle cx="44" cy="44" r={r} fill="none" stroke="var(--nq-line)" strokeWidth="6" />
          <circle
            cx="44"
            cy="44"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${c}`}
            transform="rotate(-90 44 44)"
            className={model.aiActive ? "nq-ops-pulse__ring--ai" : undefined}
          />
          <circle cx="44" cy="44" r="10" fill={color} opacity="0.35" />
          <circle cx="44" cy="44" r="5" fill={color} />
        </svg>
      </div>
      <OpsPulseCopy model={model} />
    </Link>
  );
}

export function OpsPulseCopy({ model }: { model: OpsPulseModel }) {
  return (
    <div className="nq-ops-pulse__panel">
      <p className="nq-ops-pulse__kicker">Nhịp AI · Trợ lý vận hành</p>
      <p className={`nq-ops-pulse__ai ${model.aiActive ? "nq-ops-pulse__ai--on" : ""}`}>{model.aiLabel}</p>
      <p className="nq-ops-pulse__insight">{model.insight}</p>
      <span className="nq-ops-pulse__cta">{model.cta} →</span>
    </div>
  );
}
