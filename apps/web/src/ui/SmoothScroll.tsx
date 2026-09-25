"use client";

import Lenis from "lenis";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect } from "react";

const PUBLIC_LENIS = new Set(["/", "/huong-dan"]);

/** Lenis chỉ trên trang công khai — ops giữ cuộn gốc cho sticky table. */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";

  useEffect(() => {
    if (!PUBLIC_LENIS.has(pathname)) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const lenis = new Lenis({
      duration: 1.05,
      smoothWheel: true,
      touchMultiplier: 1.2,
    });

    let raf = 0;
    function frame(t: number) {
      lenis.raf(t);
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
    };
  }, [pathname]);

  return <>{children}</>;
}
