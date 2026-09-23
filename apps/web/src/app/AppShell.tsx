"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Fragment, ReactNode, useEffect, useRef, useState } from "react";
import { apiGet } from "../lib/api";
import { canAccess, clearSession, getName, getToken, isChuQuan, isManager, roleLabel } from "../lib/session";
import { beat } from "../lib/motion";import { Icon, iconForHref } from "../ui/icons";
import { Tour } from "../ui/tour";
import { Logo } from "../ui/Logo";
import { CopilotPane } from "../ui/copilot/CopilotPane";
import { FloatingChatHead } from "../ui/chat/FloatingChatHead";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

/** `short` là nhãn cho thanh dưới dạng pill — chỗ hẹp, chữ dài sẽ gãy dòng. */
type LinkItem = { href: string; label: string; short?: string; group?: "experience" };

const EXP_GROUP: LinkItem["group"] = "experience";

const COPILOT_LAUNCHER_ROUTES = new Set([
  "/lich-tuan",
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
  { href: "/lich-tuan", label: "Lịch tuần", short: "Lịch" },
  { href: "/phieu", label: "Phiếu", short: "Phiếu" },
  { href: "/inbox", label: "Trao đổi", short: "Duyệt" },
  { href: "/copilot", label: "Trợ lý", short: "Trợ lý" },
];

const ADMIN_PRIMARY: LinkItem[] = [
  { href: "/hom-nay", label: "Hôm nay" },
  { href: "/lich-tuan", label: "Lịch tuần", short: "Lịch" },
  { href: "/phieu", label: "Phiếu", short: "Phiếu" },
  { href: "/inbox", label: "Trao đổi", short: "Duyệt" },
  { href: "/cam-nang", label: "Cẩm nang", short: "Luật" },
  { href: "/copilot", label: "Trợ lý", short: "Trợ lý" },
];

const MORE: LinkItem[] = [
  { href: "/chat", label: "Chat nội bộ" },
  { href: "/huong-dan", label: "Bản đồ hệ thống" },
  { href: "/cuoc-hop", label: "Họp & gửi nhóm" },
  { href: "/tkb", label: "Tải ảnh lịch bận" },
  { href: "/quay", label: "Quầy" },
  { href: "/pha", label: "Pha chế" },
  { href: "/inbox", label: "Hộp thư" },
  { href: "/lich-tuan", label: "Lịch tuần" },
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
  { href: "/khao-sat-gia", label: "Khảo sát giá" },
  { href: "/nguoi", label: "Người dùng" },
  // ── Grand AI Experience ──
  { href: "/quanverse", label: "QUÁNVERSE · Living Map", group: EXP_GROUP },
  { href: "/quanverse/war-room", label: "War Room · Mô phỏng", group: EXP_GROUP },
  { href: "/quanverse/shift-rescue", label: "Shift Rescue · Cứu ca", group: EXP_GROUP },
  { href: "/quanverse/rules", label: "Quán tự viết luật", group: EXP_GROUP },
  { href: "/quanverse/spatial-memory", label: "HỒN QUÁN · Ký ức & Tour", group: EXP_GROUP },
];


export function AppShell({ children }: { children: ReactNode }) {
  // Tôn trọng ý muốn giảm chuyển động: bảng "Thêm" vẫn mở/đóng, chỉ là đổi
  // trạng thái tức thì thay vì trượt — nội dung không đổi, chỉ bỏ phần chuyển.
  const reduced = useReducedMotion() ?? false;
  const path = usePathname();
  const router = useRouter();
  const moreRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [token, setToken] = useState("");

  useEffect(() => {
    let cancelled = false;
    const storedToken = getToken();
    const storedName = getName();
    setToken(storedToken);
    setName(storedName);
    setReady(false);

    if (!storedToken) {
      setRole("");
      setReady(true);
      return () => {
        cancelled = true;
      };
    }

    apiGet<{ role: string; nv_id: string }>("/api/v1/me")
      .then((me) => {
        if (cancelled) return;
        // Quyền từ máy chủ là nguồn sự thật. Không dùng vai trò cũ trong
        // localStorage để mở một trang quản trị.
        setRole(me.role);
        sessionStorage.setItem("nq_role", me.role);
        sessionStorage.setItem("nq_nv", me.nv_id);
        localStorage.setItem("nq_role", me.role);
        localStorage.setItem("nq_nv", me.nv_id);
      })
      .catch(() => {
        // Không xác minh được thì đóng quyền, không tin dữ liệu vai trò cũ.
        if (!cancelled) setRole("__unverified__");
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });

    return () => {
      cancelled = true;
    };
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
  const wide = path === "/lich-tuan" || path === "/roster" || path === "/cuoc-hop" || path === "/inbox" || path === "/quay" || path === "/chat";

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-[var(--nq-bg)] text-[var(--nq-fg)] font-sans selection:bg-[var(--nq-copper)] selection:text-[#0e0c0a] flex flex-col relative z-10">
      <header className="fixed top-0 left-0 w-full z-40 border-b border-[var(--nq-line)] bg-[var(--nq-bg)]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-3 px-4 md:gap-4 md:px-8">
          <Logo href={token ? "/hom-nay" : "/"} />

          {token ? (
            <nav className="hidden min-w-0 flex-1 items-center justify-center gap-2 lg:flex xl:gap-4" aria-label="Chính">
              {primary.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  /* `min-h-11` (44px) + padding: vùng bấm của điều hướng chính phải
                     đủ lớn cho ngón tay. Trước đây link chỉ cao 21px (đo trên bản
                     render), dưới cả ngưỡng 24px của WCAG 2.5.8 — nhân viên đứng
                     quầy bấm trên máy tính bảng rất dễ trượt sang mục bên cạnh.
                     `rounded-full` + hover nền để vùng bấm nhìn thấy được. */
                  className={`flex shrink-0 min-h-11 items-center gap-1.5 whitespace-nowrap rounded-full px-2 text-2xs font-bold uppercase tracking-wide transition-colors xl:gap-2 xl:px-3 xl:text-xs ${path === l.href ? "bg-[var(--nq-accent-soft)] text-[var(--nq-copper)] shadow-[inset_0_-2px_0_var(--nq-copper)]" : "text-[var(--nq-dim)] hover:bg-[var(--nq-accent-soft)] hover:text-[var(--nq-fg)]"}`}
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
                  className={`flex min-h-11 items-center gap-1.5 whitespace-nowrap rounded-full px-2 text-2xs font-bold uppercase tracking-wide transition-colors xl:gap-2 xl:px-3 xl:text-xs ${open ? "bg-[var(--nq-accent-soft)] text-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:bg-[var(--nq-accent-soft)] hover:text-[var(--nq-fg)]"}`}
                  aria-expanded={open}
                  data-tour="nav-them"
                >
                  <Icon name="them" size={16} />
                  Thêm
                </button>
                <AnimatePresence>
                  {open && (
                    <motion.div
                      initial={reduced ? {} : { opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={reduced ? {} : { opacity: 0, y: 8 }}
                      transition={beat("settle")}
                      role="menu"
                      className="nq-more-panel"
                    >
                      {more.map((l, i) => (
                        <Fragment key={l.href}>
                          {l.group === "experience" &&
                            (i === 0 || more[i - 1]?.group !== "experience") && (
                              <div className="nq-more-group" role="presentation">
                                Trải nghiệm AI
                              </div>
                            )}
                          <Link
                            href={l.href}
                            role="menuitem"
                            onClick={() => setOpen(false)}
                          >
                            {l.group === "experience" ? (
                              <span className="flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--nq-copper)]" />
                                <span>{l.label.replace(/^QUÁNVERSE · |^War Room · |^Shift Rescue · |^HỒN QUÁN · /, "")}</span>
                              </span>
                            ) : (
                              l.label
                            )}
                          </Link>
                        </Fragment>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </nav>
          ) : (
            <div className="flex-1" />
          )}

          <div className="ml-auto flex shrink-0 items-center gap-2 text-2xs font-mono uppercase tracking-wide md:gap-3 xl:text-xs">
            {ready && token ? (
              <>
                <span className="hidden max-w-[10rem] truncate text-[var(--nq-dim)] lg:inline-block xl:max-w-[14rem]">
                  {name} <span className="text-[var(--nq-copper)]">[{roleLabel(role)}]</span>
                </span>
                <button
                  type="button"
                  onClick={logout}
                  className="nq-cta nq-cta--ghost nq-cta--sm"
                >
                  Thoát
                </button>
              </>
            ) : (
              <Link href="/login" className="nq-cta nq-cta--primary nq-cta--sm">
                Đăng nhập
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className={`flex-1 px-4 md:px-8 pt-16 ${wide ? "w-full max-w-none" : "max-w-[1280px] mx-auto w-full"}`} id="nq-content">
        {!ready ? (
          <div className="nq-page nq-page--center py-16 text-center" role="status">
            <p className="nq-muted" style={{ margin: 0 }}>Đang kiểm tra quyền truy cập…</p>
          </div>
        ) : token && role && !canAccess(role, path) ? (
          <div className="nq-page nq-page--center py-16 text-center">
            <h1 className="nq-gate-title">Không đủ quyền truy cập</h1>
            <p className="nq-muted mx-auto" style={{ margin: "var(--nq-s3) auto 0", maxWidth: "46ch" }}>
              {path === "/vet"
                ? "Bạn không được uỷ quyền để xem vết hệ thống. Chỉ Quản lý và Chủ quán được phép truy cập."
                : "Tài khoản hiện tại không có quyền truy cập trang này."}
            </p>
          </div>
        ) : (
          children
        )}
      </main>
      {token ? (
        <nav className="md:hidden fixed bottom-0 left-0 w-full bg-[var(--nq-bg)]/90 backdrop-blur-md border-t border-[var(--nq-line)] flex justify-around items-center p-2 z-40 pb-safe" aria-label="Lối tắt">
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
              <span className="text-2xs font-bold uppercase tracking-widest">{l.short ?? l.label}</span>
            </Link>
          ))}
          <Link
            href="/them"
            className={`flex flex-col items-center gap-1 p-2 transition-colors ${path === "/them" ? "text-[var(--nq-copper)]" : "text-[var(--nq-dim)]"}`}
            data-tour="nav-them"
            aria-current={path === "/them" ? "page" : undefined}
          >
            <Icon name="them" size={24} />
            <span className="text-2xs font-bold uppercase tracking-widest">Thêm</span>
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
