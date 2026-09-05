"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useRef, useState } from "react";
import { canAccess, clearSession, getName, getRole, getToken, isChuQuan, isManager, roleLabel } from "../lib/session";
import { Icon, iconForHref } from "../ui/icons";
import { Tour } from "../ui/tour";
import { Logo } from "../ui/Logo";
import { CopilotPane } from "../ui/copilot/CopilotPane";
import { FloatingChatHead } from "../ui/chat/FloatingChatHead";
import { motion, AnimatePresence } from "framer-motion";

/** `short` là nhãn cho thanh dưới dạng pill — chỗ hẹp, chữ dài sẽ gãy dòng. */
type LinkItem = { href: string; label: string; short?: string };

const COPILOT_LAUNCHER_ROUTES = new Set([
  "/roster",
  "/qr",
  "/phieu",
  "/treo",
  "/cong-bang",
  "/tkb",
  "/handover",
  "/doi-ca",
  "/cam-nang",
]);

/** `data-tour` để tour hướng dẫn trỏ vào đúng lối vào của từng việc. */
function tourId(href: string): string {
  return `nav-${href.replace(/^\//, "")}`;
}

const STAFF_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/chat", label: "Chat nội bộ", short: "Chat" },
  { href: "/cuoc-hop", label: "Họp & Giao ca", short: "Họp" },
  { href: "/quay", label: "Quầy", short: "Quầy" },
  { href: "/pha", label: "Pha chế", short: "Pha" },
  { href: "/tkb", label: "Lịch bận", short: "Lịch bận" },
];

const MANAGER_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/chat", label: "Chat nội bộ", short: "Chat" },
  { href: "/cuoc-hop", label: "Họp & Giao ca", short: "Họp" },
  { href: "/roster", label: "Lịch tuần", short: "Lịch" },
  { href: "/inbox", label: "Hộp thư", short: "Hộp thư" },
  { href: "/quay", label: "Quầy", short: "Quầy" },
  { href: "/tkb", label: "Lịch bận", short: "Lịch bận" },
];

const ADMIN_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/chat", label: "Chat nội bộ", short: "Chat" },
  { href: "/cuoc-hop", label: "Họp & Giao ca", short: "Họp" },
  { href: "/nguoi", label: "Người dùng", short: "Người" },
  { href: "/menu", label: "Menu & giá", short: "Menu" },
  { href: "/roster", label: "Lịch tuần", short: "Lịch" },
  { href: "/tkb", label: "Lịch bận", short: "Lịch bận" },
];

const MORE: LinkItem[] = [
  { href: "/chat", label: "Chat nội bộ" },
  { href: "/huong-dan", label: "Bản đồ hệ thống" },
  { href: "/cuoc-hop", label: "Họp & gửi nhóm" },
  { href: "/tkb", label: "Tải ảnh lịch bận" },
  { href: "/quay", label: "Quầy" },
  { href: "/pha", label: "Pha chế" },
  { href: "/inbox", label: "Hộp thư" },
  { href: "/roster", label: "Lịch tuần" },
  { href: "/page-quan", label: "Page quán (FB)" },
  { href: "/page-quan/fb-inbox", label: "Hộp thư Fanpage (duyệt)" },
  { href: "/page-quan/dat-ban", label: "Sơ đồ & Đặt bàn" },
  { href: "/ai-learning", label: "Học từ phản hồi AI" },
  { href: "/skills", label: "Bộ Kỹ năng AI (13/13)" },
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
  const moreRef = useRef<HTMLDivElement>(null);
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

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const primary = isChuQuan(role) ? ADMIN_PRIMARY : isManager(role) ? MANAGER_PRIMARY : STAFF_PRIMARY;
  const more = MORE.filter((x) => !primary.some((p) => p.href === x.href) && canAccess(role, x.href));
  const wide = path === "/roster" || path === "/cuoc-hop" || path === "/inbox" || path === "/quay" || path === "/chat";

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-[var(--nq-bg)] text-[var(--nq-fg)] font-sans selection:bg-[var(--nq-copper)] selection:text-[#0e0c0a] flex flex-col relative z-10">
      <header className="fixed top-0 left-0 w-full z-40 border-b-2 border-[var(--nq-dim)] bg-[var(--nq-bg)]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-3 px-4 md:gap-4 md:px-8">
          <Logo href={token ? "/hom-nay" : "/"} />

          {token ? (
            <nav className="hidden min-w-0 flex-1 items-center justify-center gap-2 lg:flex xl:gap-4" aria-label="Chính">
              {primary.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`flex shrink-0 items-center gap-1.5 whitespace-nowrap text-[11px] font-bold uppercase tracking-wide transition-colors xl:gap-2 xl:text-xs ${path === l.href ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                  data-tour={tourId(l.href)}
                  aria-current={path === l.href ? "page" : undefined}
                >
                  <Icon name={iconForHref(l.href)} size={16} />
                  <span className="hidden xl:inline">{l.label}</span>
                  <span className="xl:hidden">{l.short ?? l.label}</span>
                </Link>
              ))}
              <div className="relative shrink-0" ref={moreRef}>
                <button
                  type="button"
                  onClick={() => setOpen((v) => !v)}
                  className={`flex items-center gap-1.5 whitespace-nowrap text-[11px] font-bold uppercase tracking-wide transition-colors xl:gap-2 xl:text-xs ${open ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                  aria-expanded={open}
                  data-tour="nav-them"
                >
                  <Icon name="them" size={16} />
                  Thêm
                </button>
                <AnimatePresence>
                  {open && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 8 }}
                      role="menu"
                      className="absolute top-full right-0 z-50 mt-2 grid w-[min(22rem,88vw)] max-h-[min(52vh,20rem)] grid-cols-2 gap-0.5 overflow-y-auto border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-1.5 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]"
                    >
                      {more.map((l) => (
                        <Link
                          key={l.href}
                          href={l.href}
                          role="menuitem"
                          onClick={() => setOpen(false)}
                          className="rounded px-2.5 py-2 text-[10px] font-semibold leading-tight text-[var(--nq-dim)] transition-colors hover:bg-[var(--nq-surface)] hover:text-[var(--nq-copper)] xl:text-[11px]"
                        >
                          {l.label}
                        </Link>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </nav>
          ) : (
            <div className="flex-1" />
          )}

          <div className="ml-auto flex shrink-0 items-center gap-2 text-[11px] font-mono uppercase tracking-wide md:gap-3 xl:text-xs">
            {ready && token ? (
              <>
                <span className="hidden max-w-[10rem] truncate text-[var(--nq-dim)] lg:inline-block xl:max-w-[14rem]">
                  {name} <span className="text-[var(--nq-copper)]">[{roleLabel(role)}]</span>
                </span>
                <button
                  type="button"
                  onClick={logout}
                  className="shrink-0 border-2 border-[var(--nq-dim)] px-3 py-1 transition-colors hover:border-[var(--nq-red)] hover:text-[var(--nq-red)]"
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
      <main className={`flex-1 px-4 md:px-8 pt-16 ${wide ? "w-full max-w-none" : "max-w-[1280px] mx-auto w-full"}`} id="nq-content">
        {token && !canAccess(role, path) ? (
          <div className="nq-page nq-page--center py-16 text-center">
            <h1 className="text-2xl font-black uppercase text-amber-500">Trang này dành cho vai trò khác</h1>
            <p className="text-sm text-neutral-400 mt-2">Bạn không đủ quyền truy cập trang này với vai trò hiện tại.</p>
          </div>
        ) : (
          children
        )}
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
      {token ? (
        <>
          {!COPILOT_LAUNCHER_ROUTES.has(path) ? <CopilotPane /> : null}
          <FloatingChatHead />
        </>
      ) : null}
      <Tour active={Boolean(token) && path === "/hom-nay"} />
    </div>
  );
}
