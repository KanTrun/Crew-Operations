"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { AppShell } from "./AppShell";

export function ConditionalShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  // Hai cửa vào (đăng nhập, đăng ký) không có thanh điều hướng: lúc đó chưa có
  // phiên, nên mọi lối tắt đều dẫn tới màn cần đăng nhập.
  if (path === "/login" || path === "/dang-ky") return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
