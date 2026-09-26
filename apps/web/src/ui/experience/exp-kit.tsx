"use client";

/** Kit cho experience register: skeleton, empty state, section head, chip. */

import type { ReactNode } from "react";
import { Icon, type IconName } from "../icons";
import { Empty } from "../kit";

export function ExpSkeleton({ rows = 4, grid = false }: { rows?: number; grid?: boolean }) {
  return (
    <div className={`nq-skeleton-wrap${grid ? " nq-skeleton__grid" : ""}`} aria-busy="true" aria-label="Đang tải">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="nq-skeleton nq-skeleton-line" style={grid ? { minHeight: "4rem" } : undefined} />
      ))}
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
    <Empty title={title} icon={<Icon name={icon} size={28} />}>
      {hint ?? null}
    </Empty>
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
  return <span className="nq-rolechip">{label}</span>;
}
