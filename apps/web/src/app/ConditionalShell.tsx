"use client";

import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { AppShell } from "./AppShell";
import { canAccess, getRole, getToken } from "../lib/session";
import { AuthGate } from "../ui/kit";

export function ConditionalShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");

  useEffect(() => {
    setToken(getToken());
    setRole(getRole());
    setReady(true);
  }, [path]);

  if (["/", "/login", "/dang-ky"].includes(path)) return <>{children}</>;
  if (!ready) return null;
  if (!token) return <AppShell><AuthGate /></AppShell>;
  if (!canAccess(role, path)) {
    return (
      <AppShell>
        <section className="nq-page">
          <p className="nq-kicker">Không đủ quyền</p>
          <h1>Trang này dành cho vai trò khác</h1>
          <p className="nq-muted">Quay về bảng Hôm nay hoặc đăng nhập bằng tài khoản phù hợp.</p>
        </section>
      </AppShell>
    );
  }
  return <AppShell>{children}</AppShell>;
}
