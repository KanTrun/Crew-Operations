"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "../../lib/api";
import { Alert, Btn, Field, Kicker } from "../../ui/kit";

type StaffProfile = {
  username: string;
  name: string;
  role: "chu_quan" | "quan_ly" | "nhan_vien";
  roleName: string;
  icon: string;
  skills: string;
};

const ACCOUNTS: StaffProfile[] = [
  { username: "hung", name: "Hùng Trần", role: "chu_quan", roleName: "Chủ quán", icon: "👑", skills: "Toàn quyền · Menu · Phân quyền" },
  { username: "lan", name: "Lan Nguyễn", role: "quan_ly", roleName: "Quản lý", icon: "👔", skills: "Xếp ca · Duyệt inbox · Phát QR" },
  { username: "minh", name: "Minh Phạm", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Pha chế · Phục vụ · SV" },
  { username: "an", name: "An Lê", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Pha chế · Thu ngân · SV" },
  { username: "bao", name: "Bảo Hoàng", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Pha chế · Kho · Fulltime" },
  { username: "chi", name: "Chi Vũ", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Thu ngân · Phục vụ · SV" },
  { username: "dung", name: "Dũng Đặng", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Kho · Phục vụ · Fulltime" },
  { username: "thao", name: "Thảo Dương", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Thu ngân · Pha chế · Fulltime" },
  { username: "quan", name: "Quân Lương", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Pha chế · Đơn QR · SV" },
  { username: "yen", name: "Yến Kiều", role: "nhan_vien", roleName: "Nhân viên", icon: "☕", skills: "Thu ngân · Kho · SV" },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterRole, setFilterRole] = useState<string>("all");

  async function handleLogin(user: string, pass: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user, password: pass }),
      });
      if (!res.ok) {
        setError("Sai tài khoản hoặc mật khẩu.");
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
      setError("Không kết nối được máy chủ (API http://localhost:8000). Kiểm tra server rồi thử lại.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Vui lòng nhập tài khoản và mật khẩu.");
      return;
    }
    void handleLogin(username.trim(), password.trim());
  }

  function quickLogin(user: string) {
    setUsername(user);
    setPassword("nhipquan");
    void handleLogin(user, "nhipquan");
  }

  const visibleAccounts = ACCOUNTS.filter((acc) => {
    if (filterRole === "all") return true;
    return acc.role === filterRole;
  });

  return (
    <main className="relative z-10 min-h-screen flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-2xl bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] p-6 sm:p-10">
        <Kicker>OS Vận hành ca · NHỊP QUÁN</Kicker>
        <h1 className="text-3xl sm:text-4xl font-black uppercase tracking-tighter text-[var(--nq-fg)] mb-2">
          Đăng nhập
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm mb-6">
          Chọn ngay nhân viên bên dưới để đăng nhập 1 chạm, hoặc nhập tài khoản thủ công.
        </p>

        {/* Danh sách 10 nhân sự bấm đăng nhập nhanh */}
        <div className="mb-8 p-4 bg-[var(--nq-surface)] border border-[var(--nq-dim)]">
          <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
            <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-copper)] font-bold">
              ⚡ Chọn nhân viên đăng nhập 1 chạm:
            </p>
            <div className="flex gap-1 text-xs">
              <button
                type="button"
                className={`px-2 py-0.5 rounded font-mono ${filterRole === "all" ? "bg-[var(--nq-copper)] text-[var(--nq-bg)] font-bold" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                onClick={() => setFilterRole("all")}
              >
                Tất cả (10)
              </button>
              <button
                type="button"
                className={`px-2 py-0.5 rounded font-mono ${filterRole === "chu_quan" ? "bg-[var(--nq-copper)] text-[var(--nq-bg)] font-bold" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                onClick={() => setFilterRole("chu_quan")}
              >
                Chủ quán
              </button>
              <button
                type="button"
                className={`px-2 py-0.5 rounded font-mono ${filterRole === "quan_ly" ? "bg-[var(--nq-copper)] text-[var(--nq-bg)] font-bold" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                onClick={() => setFilterRole("quan_ly")}
              >
                Quản lý
              </button>
              <button
                type="button"
                className={`px-2 py-0.5 rounded font-mono ${filterRole === "nhan_vien" ? "bg-[var(--nq-copper)] text-[var(--nq-bg)] font-bold" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
                onClick={() => setFilterRole("nhan_vien")}
              >
                Nhân viên
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
            {visibleAccounts.map((acc) => (
              <button
                key={acc.username}
                type="button"
                disabled={loading}
                onClick={() => quickLogin(acc.username)}
                className="p-2.5 text-xs font-mono border border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:bg-[var(--nq-surface-hi)] transition-all text-left flex items-start justify-between group"
              >
                <div>
                  <div className="font-bold text-[var(--nq-fg)] group-hover:text-[var(--nq-copper)] flex items-center gap-1.5">
                    <span>{acc.icon}</span>
                    <span>{acc.name}</span>
                    <span className="text-[var(--nq-dim)] text-[10px]">(@{acc.username})</span>
                  </div>
                  <div className="text-[11px] text-[var(--nq-dim)] mt-0.5">
                    {acc.skills}
                  </div>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                  acc.role === "chu_quan"
                    ? "bg-amber-900/30 text-amber-400 border border-amber-800"
                    : acc.role === "quan_ly"
                    ? "bg-blue-900/30 text-blue-400 border border-blue-800"
                    : "bg-emerald-900/30 text-emerald-400 border border-emerald-800"
                }`}>
                  {acc.roleName}
                </span>
              </button>
            ))}
          </div>
        </div>

        {error ? <Alert kind="err">{error}</Alert> : null}

        {/* Form nhập tay */}
        <form onSubmit={onSubmit} className="space-y-4 pt-2 border-t border-[var(--nq-border)]">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field label="Tài khoản">
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                placeholder="lan / minh / hung..."
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-2.5 text-[var(--nq-fg)] font-mono text-sm focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>

            <Field label="Mật khẩu">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="Mặc định: nhipquan"
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-2.5 text-[var(--nq-fg)] font-mono text-sm focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>
          </div>

          <div className="pt-2">
            <Btn type="submit" variant="primary" block busy={loading} busyLabel="Đang đăng nhập…">
              Vào hệ thống
            </Btn>
          </div>
        </form>
      </div>
    </main>
  );
}
