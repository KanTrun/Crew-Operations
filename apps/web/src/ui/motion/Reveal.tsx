"use client";

import { m, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { fadeOnly, fadeUp, stagger } from "./presets";

export function Reveal({
  children,
  className = "",
  as: Tag = "div",
  staggerChildren = false,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "ul" | "li" | "header";
  staggerChildren?: boolean;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  const variants = reduce ? fadeOnly : fadeUp;
  const Comp = m[Tag];

  return (
    <Comp
      className={className}
      initial="hidden"
      animate="show"
      variants={staggerChildren ? { ...variants, ...stagger() } : variants}
      transition={delay ? { delay } : undefined}
    >
      {children}
    </Comp>
  );
}

export function RevealItem({ children, className = "" }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <m.div className={className} variants={reduce ? fadeOnly : fadeUp}>
      {children}
    </m.div>
  );
}
