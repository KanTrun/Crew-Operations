"use client";

import { AnimatePresence } from "framer-motion";
import type { ReactNode } from "react";

export function Presence({
  children,
  mode = "sync",
}: {
  children: ReactNode;
  mode?: "sync" | "wait" | "popLayout";
}) {
  return <AnimatePresence mode={mode}>{children}</AnimatePresence>;
}
