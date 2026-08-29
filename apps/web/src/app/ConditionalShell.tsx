"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { AppShell } from "./AppShell";

/** Trang marketing / cửa auth: full-bleed, không thanh điều hướng ops. */
const BARE = new Set(["/", "/login", "/dang-ky"]);

export function ConditionalShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  if (BARE.has(path)) return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
