"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { clearSession, getName, getRole, getToken, isManager, roleLabel } from "../lib/session";
import { Icon, iconForHref } from "../ui/icons";
import { Tour } from "../ui/tour";
import { Logo } from "../ui/Logo";
import { motion, AnimatePresence } from "framer-motion";

/** `short` là nhãn cho thanh dưới dạng pill — chỗ hẹp, chữ dài sẽ gãy dòng. */
type LinkItem = { href: string; label: string; short?: string };

/** `data-tour` để tour hướng dẫn trỏ vào đúng lối vào của từng việc. */
function tourId(href: string): string {
  return `nav-${href.replace(/^\//, "")}`;
}

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
  { href: "/huong-dan", label: "Hướng dẫn cho người mới" },
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
    <div className="min-h-screen bg-[var(--nq-bg)] text-[var(--nq-fg)] font-sans selection:bg-[var(--nq-copper)] selection:text-[#0e0c0a] flex flex-col relative z-10">
      <header className="fixed top-0 left-0 w-full z-40 bg-[var(--nq-bg)]/80 backdrop-blur-md border-b-2 border-[var(--nq-dim)]">
        <div className="max-w-[1440px] mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <Link href={token ? "/hom-nay" : "/"} className="group transition-colors">
            <Logo />
          </Link>
          {token ? (
            <nav className="hidden md:flex items-center gap-8" aria-label="Chính">
              {primary.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`flex items-center gap-2 font-bold uppercase tracking-widest text-sm transition-colors ${path === l.href ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                  data-tour={tourId(l.href)}
                  aria-current={path === l.href ? "page" : undefined}
                >
                  <Icon name={iconForHref(l.href)} size={18} />
                  {l.label}
                </Link>
              ))}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setOpen((v) => !v)}
                  className={`flex items-center gap-2 font-bold uppercase tracking-widest text-sm transition-colors ${open ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                  aria-expanded={open}
                  data-tour="nav-them"
                >
                  <Icon name="them" size={18} />
                  Thêm
                </button>
                <AnimatePresence>
                  {open && (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute top-full right-0 mt-4 w-64 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] py-2 z-50"
                    >
                      {more.map((l) => (
                        <Link 
                          key={l.href} 
                          href={l.href} 
                          onClick={() => setOpen(false)}
                          className="block px-6 py-3 font-bold uppercase tracking-widest text-sm text-[var(--nq-dim)] hover:text-[var(--nq-copper)] hover:bg-[var(--nq-surface)] transition-colors"
                        >
                          {l.label}
                        </Link>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </nav>
          ) : null}
          <div className="flex items-center gap-4 text-sm font-mono uppercase tracking-widest">
            {ready && token ? (
              <>
                <span className="hidden md:inline-block text-[var(--nq-dim)]">
                  {name} <span className="text-[var(--nq-copper)]">[{roleLabel(role)}]</span>
                </span>
                <button 
                  type="button" 
                  onClick={logout}
                  className="border-2 border-[var(--nq-dim)] px-4 py-1 hover:border-[var(--nq-red)] hover:text-[var(--nq-red)] transition-colors"
                >
                  Thoát
                </button>
              </>
            ) : (
              <Link 
                href="/login"
                className="border-2 border-[var(--nq-copper)] text-[var(--nq-copper)] px-4 py-1 hover:bg-[var(--nq-copper)] hover:text-[#0e0c0a] transition-colors"
              >
                Đăng nhập
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className={`flex-1 pt-16 ${wide ? "w-full" : "max-w-[1440px] mx-auto w-full"}`} id="nq-content">
        {children}
      </main>
      {token ? (
        <nav className="md:hidden fixed bottom-0 left-0 w-full bg-[var(--nq-bg)]/90 backdrop-blur-md border-t-2 border-[var(--nq-dim)] flex justify-around items-center p-2 z-40 pb-safe" aria-label="Lối tắt">
          {primary.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`flex flex-col items-center gap-1 p-2 transition-colors ${path === l.href ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)]"}`}
              data-tour={tourId(l.href)}
              aria-current={path === l.href ? "page" : undefined}
              aria-label={l.label}
            >
              <Icon name={iconForHref(l.href)} size={24} />
              <span className="text-[10px] font-bold uppercase tracking-widest">{l.short ?? l.label}</span>
            </Link>
          ))}
          <Link
            href="/them"
            className={`flex flex-col items-center gap-1 p-2 transition-colors ${path === "/them" ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)]"}`}
            data-tour="nav-them"
            aria-current={path === "/them" ? "page" : undefined}
          >
            <Icon name="them" size={24} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Thêm</span>
          </Link>
        </nav>
      ) : null}
      <Tour active={Boolean(token) && path === "/hom-nay"} />
    </div>
  );
}
