"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "../lib/api";
import { getToken, isManager } from "../lib/session";

type StaffProfile = {
  username: string;
  name: string;
  role: "chu_quan" | "quan_ly" | "nhan_vien";
  roleName: string;
  icon: string;
  desc: string;
  badgeColor: string;
};

const MAIN_ROLES: StaffProfile[] = [
  {
    username: "hung",
    name: "Hùng Trần",
    role: "chu_quan",
    roleName: "Chủ quán",
    icon: "👑",
    desc: "Toàn quyền quản trị · Cấu hình menu & công thức · Báo cáo chi phí · Giám sát tuân thủ SOP chuỗi",
    badgeColor: "border-emerald-700/60 bg-emerald-950/40 text-emerald-300",
  },
  {
    username: "lan",
    name: "Lan Nguyễn",
    role: "quan_ly",
    roleName: "Quản lý ca",
    icon: "👔",
    desc: "Xếp lịch tuần · Điều hành họp ca AI · Kiểm soát SOP · Huấn luyện nhân viên · Duyệt việc treo",
    badgeColor: "border-amber-700/60 bg-amber-950/40 text-amber-300",
  },
  {
    username: "minh",
    name: "Minh Phạm",
    role: "nhan_vien",
    roleName: "Nhân viên ca",
    icon: "☕",
    desc: "Màn hình POS & KDS quầy bar · Xem lịch đi làm cá nhân · Chợ đổi ca · Phiếu mở/đóng ca",
    badgeColor: "border-neutral-700/60 bg-neutral-900/60 text-neutral-200",
  },
];

const OTHER_STAFF = [
  { username: "an", name: "An Lê", roleName: "Thu ngân & Barista", icon: "☕" },
  { username: "bao", name: "Bảo Hoàng", roleName: "Barista & Kho", icon: "☕" },
  { username: "chi", name: "Chi Vũ", roleName: "Thu ngân & Phục vụ", icon: "☕" },
  { username: "thao", name: "Thảo Dương", roleName: "Thu ngân & Pha chế", icon: "☕" },
  { username: "dung", name: "Dũng Đặng", roleName: "Kho & Phục vụ", icon: "☕" },
  { username: "quan", name: "Quân Lương", roleName: "Pha chế & Đơn QR", icon: "☕" },
  { username: "yen", name: "Yến Kiều", roleName: "Thu ngân & Kho", icon: "☕" },
];

export default function HomePage() {
  const router = useRouter();
  const [loadingUser, setLoadingUser] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasSession, setHasSession] = useState(false);

  useEffect(() => {
    if (getToken()) {
      setHasSession(true);
    }
  }, []);

  async function handleQuickLogin(user: string) {
    setLoadingUser(user);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user, password: "nhipquan" }),
      });
      if (!res.ok) {
        setError("Không thể đăng nhập. Kiểm tra backend API.");
        return;
      }
      const data = (await res.json()) as {
        token: string;
        role: string;
        display_name: string;
        nv_id: string;
      };
      sessionStorage.setItem("nq_token", data.token);
      sessionStorage.setItem("nq_role", data.role);
      sessionStorage.setItem("nq_name", data.display_name);
      sessionStorage.setItem("nq_nv", data.nv_id);

      router.push("/hom-nay");
    } catch {
      setError("Lỗi kết nối máy chủ API http://localhost:8000. Vui lòng kiểm tra Docker stack.");
    } finally {
      setLoadingUser(null);
    }
  }

  return (
    <main className="min-h-screen bg-[var(--nq-bg)] text-[var(--nq-fg)] selection:bg-[var(--nq-copper)] selection:text-black">
      {/* Background Subtle Gradient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[420px] bg-radial from-amber-900/15 via-transparent to-transparent pointer-events-none blur-3xl"></div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-12">
        {/* ========================================================================= */}
        {/* HERO SECTION                                                             */}
        {/* ========================================================================= */}
        <header className="text-center space-y-4 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-neutral-900/90 border border-amber-700/40 shadow-inner">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-mono font-bold tracking-wider text-amber-300 uppercase">
              NHỊP QUÁN • VẬN HÀNH CA CAO CẤP
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black uppercase tracking-tight text-neutral-100 font-serif">
            HỆ THỐNG VẬN HÀNH QUÁN{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500">
              3 VAI
            </span>
          </h1>

          <p className="text-sm sm:text-base text-neutral-300 font-sans leading-relaxed">
            Nền tảng vận hành ca liền mạch: Tự động hóa họp giao ca bằng AI, Kiểm soát tuân thủ SOP,
            Xếp lịch tuần phân quyền & Màn hình POS/KDS quầy bar thông minh.
          </p>

          {hasSession && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => router.push("/hom-nay")}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-neutral-950 font-bold text-sm shadow-lg transition-all"
              >
                <span>⚡</span> Tiếp tục phiên làm việc ca hôm nay →
              </button>
            </div>
          )}

          {error && (
            <div className="p-3 bg-rose-950/60 border border-rose-700 text-rose-200 text-xs rounded-lg">
              {error}
            </div>
          )}
        </header>

        {/* ========================================================================= */}
        {/* 3 ROLE HERO CARDS (1-CLICK QUICK ACCESS)                                 */}
        {/* ========================================================================= */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-neutral-400">
              Chọn vai trò để vào ca (Đăng nhập 1 chạm)
            </h2>
            <span className="text-xs text-neutral-500 font-mono">Mật khẩu mặc định: nhipquan</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {MAIN_ROLES.map((roleItem) => {
              const isBusy = loadingUser === roleItem.username;
              return (
                <div
                  key={roleItem.username}
                  onClick={() => !isBusy && handleQuickLogin(roleItem.username)}
                  className={`group cursor-pointer relative p-6 rounded-2xl bg-neutral-900/80 border border-neutral-800 hover:border-amber-600/70 hover:bg-neutral-900 transition-all duration-300 shadow-xl flex flex-col justify-between space-y-6 ${
                    isBusy ? "opacity-60 pointer-events-none" : ""
                  }`}
                >
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-neutral-800 border border-neutral-700 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                          {roleItem.icon}
                        </div>
                        <div>
                          <h3 className="font-bold text-lg text-neutral-100 group-hover:text-amber-300 transition-colors">
                            {roleItem.name}
                          </h3>
                          <span className="text-xs font-mono text-neutral-400">
                            @{roleItem.username}
                          </span>
                        </div>
                      </div>

                      <span
                        className={`text-[11px] font-mono font-bold px-2.5 py-1 rounded-full border ${roleItem.badgeColor}`}
                      >
                        {roleItem.roleName}
                      </span>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-neutral-400 leading-relaxed min-h-[48px]">
                      {roleItem.desc}
                    </p>
                  </div>

                  {/* Button Action */}
                  <div className="pt-4 border-t border-neutral-800/80 flex items-center justify-between">
                    <span className="text-xs font-bold text-neutral-300 group-hover:text-amber-400 transition-colors flex items-center gap-1.5">
                      {isBusy ? "Đang vào ca…" : `Vào vai ${roleItem.roleName}`}
                    </span>
                    <span className="text-neutral-500 group-hover:text-amber-400 group-hover:translate-x-1 transition-all">
                      →
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ========================================================================= */}
        {/* OTHER STAFF (QUICK SELECTION FOR TESTING)                                 */}
        {/* ========================================================================= */}
        <section className="p-5 rounded-2xl bg-neutral-950/60 border border-neutral-800/80 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-xs font-mono font-bold text-neutral-400 uppercase tracking-wider">
              👥 Nhân sự ca khác (Chọn nhanh):
            </span>
            <span className="text-xs text-neutral-500">Bấm vào bất kỳ bạn nào để vào ca</span>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {OTHER_STAFF.map((staff) => (
              <button
                key={staff.username}
                type="button"
                onClick={() => handleQuickLogin(staff.username)}
                disabled={loadingUser === staff.username}
                className="shrink-0 px-3 py-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 hover:border-amber-700 text-xs text-neutral-200 transition-all flex items-center gap-2"
              >
                <span>{staff.icon}</span>
                <span className="font-bold">{staff.name}</span>
                <span className="text-[10px] text-neutral-400 font-mono">({staff.roleName})</span>
              </button>
            ))}
          </div>
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

