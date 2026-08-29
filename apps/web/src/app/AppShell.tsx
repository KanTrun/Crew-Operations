"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { canAccess, clearSession, getName, getRole, getToken, isChuQuan, isManager, roleLabel } from "../lib/session";
import { Logo } from "../ui/Logo";

type LinkItem = { href: string; label: string; short?: string };

const STAFF_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/quay", label: "Quầy" },
  { href: "/pha", label: "Pha chế" },
  { href: "/phieu", label: "Phiếu" },
];

const MANAGER_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/roster", label: "Lịch tuần" },
  { href: "/inbox", label: "Hộp thư" },
  { href: "/quay", label: "Quầy" },
  { href: "/pha", label: "Pha chế" },
];

const ADMIN_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/nguoi", label: "Người dùng" },
  { href: "/menu", label: "Menu & giá" },
  { href: "/roster", label: "Lịch tuần" },
  { href: "/cam-nang", label: "Cẩm nang" },
];

const MORE: LinkItem[] = [
  { href: "/huong-dan", label: "Bản đồ hệ thống" },
  { href: "/quay", label: "Quầy" },
  { href: "/pha", label: "Pha chế" },
  { href: "/inbox", label: "Hộp thư" },
  { href: "/roster", label: "Lịch tuần" },
  { href: "/page-quan", label: "Page quán (Facebook)" },
  { href: "/cong-bang", label: "Công bằng" },
  { href: "/toi", label: "Ca của tôi" },
  { href: "/phieu", label: "Phiếu" },
  { href: "/treo", label: "Việc treo" },
  { href: "/doi-ca", label: "Chợ đổi ca" },
  { href: "/qr", label: "Điểm danh QR" },
  { href: "/tieu-thu", label: "Sổ tiêu thụ" },
  { href: "/hao-phi", label: "Hao phí" },
  { href: "/sop", label: "Hỏi SOP" },
  { href: "/handover", label: "Bàn giao" },
  { href: "/vet", label: "Vết hệ thống" },
  { href: "/cam-nang", label: "Cẩm nang" },
  { href: "/menu", label: "Menu & giá" },
  { href: "/nguoi", label: "Người dùng" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [token, setToken] = useState("");

  useEffect(() => {
    setToken(getToken());
    setRole(getRole());
    setName(getName());
    setReady(true);
  }, [path]);

  const primary = isChuQuan(role) ? ADMIN_PRIMARY : isManager(role) ? MANAGER_PRIMARY : STAFF_PRIMARY;
  const more = MORE.filter((x) => !primary.some((p) => p.href === x.href) && canAccess(role, x.href));
  const wide = path === "/roster";

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <div className="nq-shell">
      <header className="nq-top">
        <div className="nq-brand">
          <Logo href={token ? "/hom-nay" : "/"} />
        </div>
        {token ? (
          <nav className="nq-nav" aria-label="Chính">
            {primary.map((l) => (
              <Link key={l.href} href={l.href} data-on={path === l.href ? "1" : "0"}>
                {l.label}
              </Link>
            ))}
            <div className="nq-more">
              <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
                Thêm
              </button>
              {open ? (
                <div className="nq-more-panel">
                  {more.map((l) => (
                    <Link key={l.href} href={l.href} onClick={() => setOpen(false)}>
                      {l.label}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          </nav>
        ) : null}
        <div className="nq-user">
          {ready && token ? (
            <>
              <span>
                {name} · {roleLabel(role)}
              </span>
              <button type="button" onClick={logout}>
                Thoát
              </button>
            </>
          ) : (
            <Link href="/login">Đăng nhập</Link>
          )}
        </div>
      </header>
      <main className="nq-main" data-wide={wide ? "1" : "0"} id="nq-content">
        {children}
      </main>
      {token ? (
        <nav className="nq-bottom" aria-label="Lối tắt">
          {primary.map((l) => (
            <Link key={l.href} href={l.href} data-on={path === l.href ? "1" : "0"}>
              {l.short ?? l.label}
            </Link>
          ))}
          <Link href="/them" data-on={path === "/them" ? "1" : "0"}>
            Thêm
          </Link>
        </nav>
      ) : null}
    </div>
  );
}
