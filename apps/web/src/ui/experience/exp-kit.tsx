"use client";

/** Kit cho experience register: skeleton, empty state, section head, chip.
 *  KhÃ´ng chá»«a trá»‘ng, khÃ´ng in chá»¯ demo â€” tráº¡ng thÃ¡i trung láº­p chuyÃªn nghiá»‡p.
 */

import type { ReactNode } from "react";
import { Icon, type IconName } from "../icons";

export function ExpSkeleton({ rows = 4, grid = false }: { rows?: number; grid?: boolean }) {
  return (
    <div className="nq-skeleton" aria-busy="true" aria-label="Äang táº£i">
      <div className="nq-skeleton__head" />
      <div className={grid ? "nq-skeleton__grid" : ""}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="nq-skeleton__row" />
        ))}
      </div>
    </div>
  );
}

export function ExpEmpty({
  icon = "info",
  title,
  hint,
}: {
  icon?: IconName;
  title: string;
  hint?: string;
}) {
  return (
    <div className="nq-exp-empty">
      <Icon name={icon} size={28} />
      <p>
        <strong>{title}</strong>
        {hint ? <br /> : null}
        {hint ? <span>{hint}</span> : null}
      </p>
    </div>
  );
}

export function ExpSectionHead({
  icon,
  title,
  desc,
  right,
}: {
  icon: IconName;
  title: string;
  desc?: string;
  right?: ReactNode;
}) {
  return (
    <div className="nq-exp-section__head">
      <Icon name={icon} size={16} />
      <h2 className="nq-exp-section__title">{title}</h2>
      {desc ? <p className="nq-exp-section__desc">{desc}</p> : null}
      <span className="nq-exp-section__spacer" />
      {right}
    </div>
  );
}

export function RoleChip({ label }: { label: string }) {
  // Chip tráº¡ng thÃ¡i trung láº­p â€” khÃ´ng mang nghÄ©a "demo/fixture".
  return <span className="nq-rolechip">{label}</span>;
}