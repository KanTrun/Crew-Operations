"use client";

import Link from "next/link";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import type { MouseEvent, ReactNode } from "react";
import { beat, springFor } from "../../lib/motion";

/**
 * Nghiêng theo con trỏ — chỉ dành cho thẻ được AI chọn là việc gấp nhất.
 *
 * Vì sao không áp cho mọi thẻ: bản cũ nghiêng cả bốn thẻ KPI như nhau, nên "thẻ
 * nào quan trọng" không đọc ra được từ chuyển động — mọi thứ đều động thì không
 * gì nổi bật. Nay đúng một thẻ mỗi trang có khoảnh khắc này, và nó trùng với
 * thẻ mà `computeOpsPulse` đánh dấu `highlightKpi`. Chuyển động trở thành một
 * kênh thông tin (chỗ này quan trọng) thay vì trang trí.
 *
 * Biên độ 4° là biên độ đọc được: lớn hơn thì chữ trên thẻ biến dạng, nhỏ hơn
 * thì không ai nhận ra có chuyển động. Độ cứng và damping lấy từ
 * `springFor("settle")` — suy ra từ chính `--nq-beat-settle`, và là tắt dần tới
 * hạn nên không bao giờ vượt đích: bảng số liệu không được rung khi người dùng
 * chỉ đang rê chuột qua.
 */
const TILT_DEG = 4;
const TILT_SPRING = springFor("settle");

function useHighlightTilt(enabled: boolean) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [TILT_DEG, -TILT_DEG]), TILT_SPRING);
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-TILT_DEG, TILT_DEG]), TILT_SPRING);

  const onMove = (e: MouseEvent<HTMLElement>) => {
    if (!enabled) return;
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
  const isHighlight = dataHighlight === "on";
  const tilt = useHighlightTilt(isHighlight && !reduced);
  const tileCls =
    accent === "warn"
      ? "nq-bento-tile nq-dash-kpi nq-dash-kpi--warn nq-ink-on-solid"
      : accent === "ok"
        ? "nq-bento-tile nq-dash-kpi nq-dash-kpi--ok nq-ink-on-solid"
        : "nq-bento-tile nq-dash-kpi";
  const highlightCls = isHighlight ? " nq-dash-kpi--pulse-hi" : "";

  const inner = (
    <>
      <strong className="nq-bento-value nq-dash-kpi-value">{value}</strong>
      <span className="nq-bento-label nq-dash-kpi-label">{label}</span>
    </>
  );

  // Thẻ thường: chỉ vào nhẹ + phản hồi bấm. Thẻ được đánh dấu: thêm nghiêng.
  const motionProps = reduced
    ? {}
    : isHighlight
      ? {
          initial: { opacity: 0, y: 10 },
          animate: { opacity: 1, y: 0 },
          transition: beat("focus", delay),
          style: { rotateX: tilt.rotateX, rotateY: tilt.rotateY, transformPerspective: 900 },
          onMouseMove: tilt.onMove,
          onMouseLeave: tilt.onLeave,
          whileHover: { scale: 1.015, transition: beat("settle") },
          whileTap: { scale: 0.985 },
        }
      : {
          initial: { opacity: 0, y: 10 },
          animate: { opacity: 1, y: 0 },
          transition: beat("focus", delay),
          whileTap: { scale: 0.985 },
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
      transition={beat("focus")}
    >
      <div className="nq-dash-strip-glow" aria-hidden />
      <div className="nq-dash-strip-text">
        <h1 className="nq-dash-strip-kicker">NHỊP QUÁN HÔM NAY</h1>
        <p className="nq-dash-strip-status">{status}</p>
        {meta ? <p className="nq-dash-strip-meta">{meta}</p> : null}
      </div>
    </motion.header>
  );
}
