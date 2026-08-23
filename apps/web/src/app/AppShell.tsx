"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { clearSession, getName, getRole, getToken, isManager, roleLabel } from "../lib/session";
import { Icon, iconForHref } from "../ui/icons";

/** `short` là nhãn cho thanh dưới dạng pill — chỗ hẹp, chữ dài sẽ gãy dòng. */
type LinkItem = { href: string; label: string; short?: string };

const STAFF_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/phieu", label: "Phiếu" },
  { href: "/toi", label: "Ca của tôi", short: "Ca tôi" },
  { href: "/treo", label: "Việc treo", short: "Treo" },
];

const MANAGER_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/roster", label: "Lịch tuần", short: "Lịch" },
  { href: "/inbox", label: "Hộp thư", short: "Hộp thư" },
  { href: "/cam-nang", label: "Cẩm nang", short: "Cẩm nang" },
];

const MORE: LinkItem[] = [
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

  const manager = isManager(role);
  const primary = manager ? MANAGER_PRIMARY : STAFF_PRIMARY;
  const more = MORE.filter((x) => !primary.some((p) => p.href === x.href));
  const wide = path === "/roster";

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <div className="nq-shell">
      <header className="nq-top">
        <Link href={token ? "/hom-nay" : "/"} className="nq-brand">
          NHỊP QUÁN
        </Link>
        {token ? (
          <nav className="nq-nav" aria-label="Chính">
            {primary.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                data-on={path === l.href ? "1" : "0"}
                aria-current={path === l.href ? "page" : undefined}
              >
                <Icon name={iconForHref(l.href)} size={18} />
                {l.label}
              </Link>
            ))}
            <div className="nq-more">
              <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
                <Icon name="them" size={18} />
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
      <main className="nq-main" id="nq-content" data-wide={wide ? "1" : "0"}>
        {children}
      </main>
      {token ? (
        <nav className="nq-bottom" aria-label="Lối tắt">
          {primary.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              data-on={path === l.href ? "1" : "0"}
              aria-current={path === l.href ? "page" : undefined}
              aria-label={l.label}
            >
              <Icon name={iconForHref(l.href)} />
              {l.short ?? l.label}
            </Link>
          ))}
          <Link
            href="/them"
            data-on={path === "/them" ? "1" : "0"}
            aria-current={path === "/them" ? "page" : undefined}
          >
            <Icon name="them" />
            Thêm
          </Link>
        </nav>
      ) : null}
    </div>
  );
}
