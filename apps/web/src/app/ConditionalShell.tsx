"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { useEffect } from "react";
import { AppShell } from "./AppShell";

export function ConditionalShell({ children }: { children: ReactNode }) {
  const path = usePathname();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [path]);

  if (path === "/" || path === "/login" || path === "/huong-dan") return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
