"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export function Logo({ href = "/", className = "" }: { href?: string; className?: string }) {
  return (
    <Link
      href={href}
      className={`group inline-flex shrink-0 items-center transition-colors ${className}`}
      aria-label="NHỊP QUÁN — về trang chủ"
    >
      <motion.svg
        width="36"
        height="36"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 overflow-visible"
        initial="hidden"
        animate="visible"
        whileHover="hover"
        aria-hidden
      >
        <motion.circle
          cx="50"
          cy="50"
          r="45"
          stroke="var(--nq-copper)"
          strokeWidth="2"
          strokeDasharray="4 8"
          variants={{
            hidden: { pathLength: 0, rotate: -90, opacity: 0 },
            visible: {
              pathLength: 1,
              rotate: 0,
              opacity: 1,
              transition: { duration: 2, ease: "easeInOut" },
            },
            hover: {
              rotate: 180,
              strokeWidth: 4,
              transition: { duration: 1, ease: "linear", repeat: Infinity },
            },
          }}
        />
        <motion.path
          d="M 30 70 L 30 30 L 50 70 L 70 30 L 70 70"
          stroke="var(--nq-fg)"
          strokeWidth="6"
          strokeLinecap="square"
          strokeLinejoin="miter"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 1.5, ease: "circOut", delay: 0.5 },
            },
            hover: {
              stroke: "var(--nq-copper)",
              scale: 1.1,
              transition: { duration: 0.3 },
            },
          }}
        />
        <motion.circle
          cx="50"
          cy="50"
          r="6"
          fill="var(--nq-red)"
          variants={{
            hidden: { scale: 0, opacity: 0 },
            visible: {
              scale: [1, 1.5, 1],
              opacity: 1,
              transition: { duration: 2, repeat: Infinity, ease: "easeInOut", delay: 1 },
            },
            hover: {
              scale: 2,
              fill: "var(--nq-copper)",
              transition: { duration: 0.3 },
            },
          }}
        />
      </motion.svg>
      <div className="ml-2.5 hidden min-w-0 flex-col justify-center sm:flex">
        <span className="text-base font-black uppercase leading-none tracking-tighter text-[var(--nq-fg)] md:text-lg">
          NHỊP QUÁN
        </span>
        <span className="mt-0.5 font-mono text-[9px] uppercase leading-none tracking-[0.28em] text-[var(--nq-copper)]">
          Digital System
        </span>
      </div>
    </Link>
  );
}
