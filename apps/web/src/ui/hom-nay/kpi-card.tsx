"use client";

import Link from "next/link";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import type { MouseEvent, ReactNode } from "react";

function useTilt(reduced: boolean) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [6, -6]), { stiffness: 260, damping: 22 });
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-6, 6]), { stiffness: 260, damping: 22 });

  const onMove = (e: MouseEvent<HTMLElement>) => {
    if (reduced) return;
    const rect = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - rect.left) / rect.width - 0.5);
    y.set((e.clientY - rect.top) / rect.height - 0.5);
  };
  const onLeave = () => {
    x.set(0);
    y.set(0);
  };
  return { rotateX, rotateY, onMove, onLeave };
}

export function KpiCard({
  value,
  label,
  href,
  accent,
  delay = 0,
  "data-highlight": dataHighlight,
}: {
  value: ReactNode;
  label: string;
  href?: string;
  accent?: "warn" | "ok" | "default";
  delay?: number;
  "data-highlight"?: string;
}) {
  const reduced = useReducedMotion() ?? false;
  const tilt = useTilt(reduced);
  const tileCls =
    accent === "warn"
      ? "nq-bento-tile nq-dash-kpi nq-dash-kpi--warn nq-ink-on-solid"
      : accent === "ok"
        ? "nq-bento-tile nq-dash-kpi nq-dash-kpi--ok nq-ink-on-solid"
        : "nq-bento-tile nq-dash-kpi";
  const highlightCls = dataHighlight === "on" ? " nq-dash-kpi--pulse-hi" : "";

  const inner = (
    <>
      <strong className="nq-bento-value nq-dash-kpi-value">{value}</strong>
      <span className="nq-bento-label nq-dash-kpi-label">{label}</span>
    </>
  );

  const motionProps = reduced
    ? {}
    : {
        initial: { opacity: 0, y: 14 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.42, delay, ease: [0.22, 1, 0.36, 1] as const },
        style: { rotateX: tilt.rotateX, rotateY: tilt.rotateY, transformPerspective: 900 },
        onMouseMove: tilt.onMove,
        onMouseLeave: tilt.onLeave,
        whileHover: { scale: 1.02, transition: { duration: 0.2 } },
        whileTap: { scale: 0.98 },
      };

  if (href) {
    return (
      <motion.div className="nq-dash-kpi-cell" {...motionProps}>
        <Link href={href} className={tileCls + highlightCls}>
          {inner}
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div className={`nq-dash-kpi-cell ${tileCls}${highlightCls}`} {...motionProps}>
      {inner}
    </motion.div>
  );
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
      <div className="nq-dash-strip-glow" aria-hidden />
      <div className="nq-dash-strip-text">
        <h1 className="nq-dash-strip-kicker">Quán hôm nay · NHỊP QUÁN</h1>
        <p className="nq-dash-strip-status">{status}</p>
        {meta ? <p className="nq-dash-strip-meta">{meta}</p> : null}
      </div>
    </motion.header>
  );
}
