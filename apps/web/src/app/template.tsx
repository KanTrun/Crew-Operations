"use client";

import { m } from "framer-motion";
import type { ReactNode } from "react";
import { pageEnter } from "../ui/motion/presets";

/** Biên đạo vào trang — nhẹ, không chặn thao tác (<400ms). */
export default function Template({ children }: { children: ReactNode }) {
  return (
    <m.div initial={pageEnter.initial} animate={pageEnter.animate} style={{ willChange: "opacity, transform" }}>
      {children}
    </m.div>
  );
}
