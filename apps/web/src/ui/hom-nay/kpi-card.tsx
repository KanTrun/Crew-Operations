"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

export function KpiCard({
  value,
  label,
  href,
  accent,
  delay = 0,
}: {
  value: ReactNode;
  label: string;
  href?: string;
  accent?: "warn" | "ok" | "default";
  delay?: number;
}) {
  const reduced = useReducedMotion() ?? false;
  const tileCls =
    accent === "warn"
      ? "nq-bento-tile nq-dash-kpi nq-dash-kpi--warn nq-ink-on-solid"
      : accent === "ok"
        ? "nq-bento-tile nq-dash-kpi nq-dash-kpi--ok nq-ink-on-solid"
        : "nq-bento-tile nq-dash-kpi";

  const inner = (
    <>
      <strong className="nq-bento-value nq-dash-kpi-value">{value}</strong>
      <span className="nq-bento-label nq-dash-kpi-label">{label}</span>
    </>
  );

  const motionProps = reduced
    ? { className: "nq-dash-kpi-cell" }
    : {
        className: "nq-dash-kpi-cell",
        initial: { opacity: 0, y: 14 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.42, delay, ease: [0.22, 1, 0.36, 1] as const },
        whileHover: { y: -3, transition: { duration: 0.18 } },
      };

  if (href) {
    return (
      <motion.div {...motionProps}>
        <Link href={href} className={tileCls}>
          {inner}
        </Link>
      </motion.div>
    );
  }

  const staticMotion = reduced
    ? { className: `nq-dash-kpi-cell ${tileCls}` }
    : {
        className: `nq-dash-kpi-cell ${tileCls}`,
        initial: { opacity: 0, y: 14 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.42, delay, ease: [0.22, 1, 0.36, 1] as const },
      };

  return <motion.div {...staticMotion}>{inner}</motion.div>;
}

export function StatusStrip({ status, meta }: { status: ReactNode; meta?: ReactNode }) {
  const reduced = useReducedMotion() ?? false;
  return (
    <motion.header
      className="nq-dash-strip"
      aria-label="Tình trạng quán"
      initial={reduced ? {} : { opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="nq-dash-strip-text">
        <p className="nq-dash-strip-kicker">NHỊP QUÁN · Ca hôm nay</p>
        <p className="nq-dash-strip-status">{status}</p>
        {meta ? <p className="nq-dash-strip-meta">{meta}</p> : null}
      </div>
    </motion.header>
  );
}
