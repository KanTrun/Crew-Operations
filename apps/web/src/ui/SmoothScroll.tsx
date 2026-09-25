"use client";

import { ReactNode } from "react";

/**
 * Pass-through — Lenis tạm tắt: sticky chapter trên landing che nút demo khi cuộn.
 * Bật lại sau khi sửa z-index / pointer-events của chapter.
 */
export function SmoothScroll({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
