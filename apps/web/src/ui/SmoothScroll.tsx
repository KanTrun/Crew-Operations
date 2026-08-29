"use client";

import { ReactNode } from "react";

/** Pass-through — giữ hook layout cho sau này (Lenis / scroll-snap). */
export function SmoothScroll({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
