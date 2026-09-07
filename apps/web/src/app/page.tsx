"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "../lib/session";
import { Logo } from "../ui/Logo";

export default function HomePage() {
  const router = useRouter();
  const [hasSession, setHasSession] = useState(false);

  useEffect(() => {
    if (getToken()) {
      setHasSession(true);
    }
  }, []);


  return (
    <main className="relative min-h-screen bg-[var(--nq-bg)] text-[var(--nq-fg)] selection:bg-[var(--nq-copper)] selection:text-black">
      <div className="pointer-events-none fixed top-[10%] left-[5%] h-[40vw] w-[40vw] rounded-full bg-[var(--nq-copper-glow)] opacity-40 blur-[120px] mix-blend-screen" />
      <div className="pointer-events-none fixed right-[5%] bottom-[10%] h-[50vw] w-[50vw] rounded-full bg-[var(--nq-red-dim)] opacity-20 blur-[150px] mix-blend-screen" />

      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-12">
        {/* Hero MapGuide (UI local) */}
        <section className="flex flex-col items-center text-center space-y-6 py-6">
          <Logo />
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-4xl font-black leading-[0.9] tracking-tighter uppercase sm:text-6xl">
            <span className="block">NHỊP</span>
            <span className="block text-[var(--nq-copper)]">QUÁN</span>
          </div>
          <p className="max-w-2xl text-base sm:text-lg text-[var(--nq-dim)] leading-relaxed">
            Hệ điều hành ca — MapGuide, AG-Meeting AI, lịch tuần & quầy bar trong một nền tảng.
          </p>
          <div className="flex w-full max-w-md flex-col gap-3 sm:flex-row sm:gap-4">
            <Link
              href="/login"
              className="nq-ink-on-solid flex-1 border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] px-6 py-4 text-center font-black tracking-widest uppercase transition-all duration-300 hover:bg-transparent hover:text-[var(--nq-copper)]"
            >
              Vào Ca
            </Link>
            <Link
              href="/huong-dan"
              className="flex-1 border-2 border-[var(--nq-dim)] bg-transparent px-6 py-4 text-center font-bold tracking-widest uppercase transition-all duration-300 hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)]"
            >
              Bản đồ hướng dẫn
            </Link>
          </div>
          {hasSession && (
            <button
              type="button"
              onClick={() => router.push("/hom-nay")}
              className="text-xs text-[var(--nq-copper)] underline"
            >
              Tiếp tục phiên làm việc →
            </button>
          )}
        </section>

        {/* Editorial block (UI local) */}
        <section className="grid grid-cols-1 items-center gap-10 md:grid-cols-2 md:gap-16">
          <div className="space-y-6">
            <h2 className="text-3xl font-black tracking-tighter text-[var(--nq-copper)] uppercase md:text-5xl">
              Một Việc
              <br />
              Một Lúc
            </h2>
            <p className="border-l-4 border-[var(--nq-copper)] pl-6 text-lg text-[var(--nq-dim)]">
              Không còn bảng tính rối rắm hay nhóm chat lộn xộn. Mọi thứ từ xếp ca, điểm danh đến kiểm kê
              đều nằm gọn trong một luồng công việc duy nhất.
            </p>
          </div>
          <div className="relative flex aspect-square flex-col justify-between border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-8 shadow-[16px_16px_0px_0px_var(--nq-copper-dim)]">
            <div className="font-mono text-sm tracking-widest text-[var(--nq-copper)] uppercase">
              Hệ Sinh Thái AI
            </div>
            <div className="text-3xl font-black uppercase sm:text-4xl">
              9 Agent
              <br />
              Chuyên
              <br />
              Trách
            </div>
            <div className="text-[var(--nq-dim)]">
              Tự động hoá vận hành, đẩy ngoại lệ lên cho con người.
            </div>
          </div>
        </section>

        {/* CTA đăng nhập — bỏ quick-login 1-chạm (phi logic trên domain công khai) */}
        <section className="flex flex-col sm:flex-row items-center justify-center gap-4 py-4">
          <Link
            href="/login"
            className="w-full sm:w-auto text-center px-10 py-4 rounded-xl border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] text-sm font-black uppercase tracking-widest text-[#0e0c0a] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]"
          >
            Đăng nhập
          </Link>
          <Link
            href="/dang-ky"
            className="w-full sm:w-auto text-center px-10 py-4 rounded-xl border-2 border-[var(--nq-dim)] text-sm font-black uppercase tracking-widest text-[var(--nq-fg)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all"
          >
            Tạo tài khoản
          </Link>
        </section>

        {/* ========================================================================= */}
        {/* CORE ECOSYSTEM MODULES (HỆ SINH THÁI 4 TRỤ CỘT)                           */}
        {/* ========================================================================= */}
        <section className="space-y-4">
          <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-neutral-400">
            Hệ sinh thái tính năng vận hành
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Feature 1 */}
            <div className="p-5 rounded-xl bg-neutral-900/60 border border-neutral-800/80 space-y-2.5">
              <div className="w-9 h-9 rounded-lg bg-amber-950/60 border border-amber-700/50 flex items-center justify-center text-lg">
                🎙️
              </div>
              <h3 className="font-bold text-sm text-neutral-100">AG-Meeting (Họp Ca AI)</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Bóc băng giọng nói, chấm điểm tuân thủ 5 tiêu chuẩn SOP, lọc Bàn VIP / Dị ứng & Huấn luyện Quản lý.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-5 rounded-xl bg-neutral-900/60 border border-neutral-800/80 space-y-2.5">
              <div className="w-9 h-9 rounded-lg bg-emerald-950/60 border border-emerald-700/50 flex items-center justify-center text-lg">
                🗓️
              </div>
              <h3 className="font-bold text-sm text-neutral-100">Roster (Lịch Tuần 3 Khung)</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Lịch cá nhân cho nhân viên, ma trận 7 ngày cho Quản lý và tính năng bấm xem chi tiết nhân sự từng ca.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-5 rounded-xl bg-neutral-900/60 border border-neutral-800/80 space-y-2.5">
              <div className="w-9 h-9 rounded-lg bg-blue-950/60 border border-blue-700/50 flex items-center justify-center text-lg">
                ☕
              </div>
              <h3 className="font-bold text-sm text-neutral-100">POS & KDS Quầy Bar</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Màn hình bán hàng cảm ứng, điều phối phiếu gọi món bar/bếp và cảnh báo món hết 86 tức thời.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-5 rounded-xl bg-neutral-900/60 border border-neutral-800/80 space-y-2.5">
              <div className="w-9 h-9 rounded-lg bg-purple-950/60 border border-purple-700/50 flex items-center justify-center text-lg">
                📖
              </div>
              <h3 className="font-bold text-sm text-neutral-100">Cẩm Nang Sống (SOP Patch)</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Tự động ghi nhận và cập nhật công thức pha chế, quy trình phục vụ từ các đề xuất đã duyệt trong ca.
              </p>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* FOOTER                                                                    */}
        {/* ========================================================================= */}
        <footer className="pt-6 border-t border-neutral-800 flex flex-wrap items-center justify-between gap-4 text-xs text-neutral-500 font-mono">
          <div>NHỊP QUÁN (Crew Operations) • Single Store Release</div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => router.push("/login")}
              className="text-neutral-400 hover:text-amber-400 underline"
            >
              Đăng nhập tài khoản khác
            </button>
            <button
              type="button"
              onClick={() => router.push("/cuoc-hop")}
              className="text-neutral-400 hover:text-amber-400 underline"
            >
              AG-Meeting
            </button>
            <button
              type="button"
              onClick={() => router.push("/roster")}
              className="text-neutral-400 hover:text-amber-400 underline"
            >
              Lịch tuần
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}

