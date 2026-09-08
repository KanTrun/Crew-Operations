"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiSend } from "../lib/api";
import { getToken, setSession } from "../lib/session";
import { Logo } from "../ui/Logo";
import { Icon } from "../ui/icons";

type LoginOut = { token: string; role: string; display_name: string; nv_id: string };
type DemoAccount = { username: string; label: string; role: string };

const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: "lan", label: "Lan Nguyễn", role: "Cửa hàng trưởng" },
  { username: "hung", label: "Hùng Trần", role: "Chủ quán" },
  { username: "nam", label: "Nam Lý", role: "Cửa hàng phó" },
  { username: "minh", label: "Minh Phạm", role: "Trưởng pha chế" },
  { username: "chi", label: "Chi Vũ", role: "Tổ trưởng thu ngân" },
  { username: "dung", label: "Dũng Đặng", role: "Trưởng kho" },
  { username: "an", label: "An Lê", role: "Nhân viên đa năng" },
  { username: "bao", label: "Bảo Hoàng", role: "Barista chính" },
  { username: "yen", label: "Yến Kiều", role: "Thu ngân ca chiều" },
  { username: "thao", label: "Thảo Dương", role: "Thu ngân ca tối" },
  { username: "quan", label: "Quân Lương", role: "Barista part-time" },
  { username: "linh", label: "Linh Ngô", role: "Phục vụ chính" },
  { username: "my", label: "Mỹ Tạ", role: "Phụ kho & sảnh" },
  { username: "khoa", label: "Khoa Đỗ", role: "Kho ca cuối tuần" },
  { username: "oanh", label: "Oanh Phan", role: "Phục vụ ca tối" },
  { username: "phuc", label: "Phúc Trịnh", role: "Barista cuối tuần" },
  { username: "son", label: "Sơn Hà", role: "Barista sáng CN" },
  { username: "rosa", label: "Rosa Võ", role: "Thử việc" },
  { username: "uyen", label: "Uyên Cao", role: "Học việc" },
];

export default function HomePage() {
  const router = useRouter();
  const [hasSession, setHasSession] = useState(false);
  const [quickLogin, setQuickLogin] = useState<string | null>(null);
  const [quickLoginError, setQuickLoginError] = useState<string | null>(null);

  useEffect(() => {
    if (getToken()) {
      setHasSession(true);
    }
  }, []);

  async function loginAs(account: DemoAccount) {
    setQuickLogin(account.username);
    setQuickLoginError(null);
    try {
      const data = await apiSend<LoginOut>("/api/v1/auth/login", {
        username: account.username,
        password: "nhipquan",
      });
      setSession(data.token, data.role, data.display_name, data.nv_id);
      router.push("/hom-nay");
    } catch (error) {
      setQuickLoginError(error instanceof ApiError && error.status === 401 ? "Tài khoản demo chưa sẵn sàng." : "Không thể vào hệ thống lúc này.");
    } finally {
      setQuickLogin(null);
    }
  }


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
              className="nq-ink-on-solid flex min-h-14 flex-1 items-center justify-center border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] px-6 py-4 text-center text-base font-black leading-none tracking-widest uppercase transition-all duration-300 hover:bg-transparent hover:text-[var(--nq-copper)] sm:text-lg"
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

        {/* Lối vào nhanh cho bộ tài khoản demo của môi trường trình diễn. */}
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

        <section className="mx-auto w-full max-w-3xl border-t border-[var(--nq-dim)] pt-6">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xs font-black uppercase tracking-widest text-[var(--nq-fg)]">Vào nhanh tài khoản demo</h2>
              <p className="mt-1 text-xs text-[var(--nq-dim)]">Chọn vai trò để bắt đầu phiên trình diễn.</p>
            </div>
            <Icon name="users" size={20} />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                onClick={() => loginAs(account)}
                disabled={quickLogin !== null}
                className="flex min-h-16 items-center justify-between border border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] px-4 text-left transition hover:border-[var(--nq-copper)] disabled:cursor-wait disabled:opacity-60"
              >
                <span>
                  <span className="block text-sm font-black text-[var(--nq-fg)]">{quickLogin === account.username ? "Đang vào…" : account.label}</span>
                  <span className="block text-[10px] uppercase tracking-wider text-[var(--nq-dim)]">{account.role}</span>
                </span>
                <Icon name="send" size={16} />
              </button>
            ))}
          </div>
          {quickLoginError && <p role="alert" className="mt-3 text-center text-xs text-[var(--nq-red)]">{quickLoginError}</p>}
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
              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--nq-copper)]/50 bg-[var(--nq-copper-dim)] text-[var(--nq-copper)]">
                <Icon name="roster" size={20} />
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

