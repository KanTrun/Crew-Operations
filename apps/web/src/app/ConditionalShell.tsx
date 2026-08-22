"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { AppShell } from "./AppShell";

export function ConditionalShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  if (path === "/login") return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
