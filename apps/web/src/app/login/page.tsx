"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "../../lib/api";
import { Alert, Btn, Field, Kicker } from "../../ui/kit";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

  return (
    <main className="relative z-10 min-h-screen flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-lg bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] p-6 sm:p-10">
        <Kicker>OS Vận hành ca · NHỊP QUÁN</Kicker>
        <h1 className="text-3xl sm:text-4xl font-black uppercase tracking-tighter text-[var(--nq-fg)] mb-2">
          Đăng nhập
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm mb-6">
          Hệ thống phân chia 3 vỏ theo vai: Nhân viên, Quản lý, Chủ quán.
        </p>

        {/* Quick login buttons for immediate testing */}
        <div className="mb-8 p-4 bg-[var(--nq-surface)] border border-[var(--nq-dim)]">
          <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-copper)] mb-3 font-bold">
            ⚡ Đăng nhập nhanh 1 chạm:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <button
              type="button"
              disabled={loading}
              onClick={() => quickLogin("minh")}
              className="p-2 text-xs font-bold font-mono uppercase border border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] bg-[var(--nq-surface-hi)] transition-colors text-left"
            >
              👤 Minh<br /><span className="text-[var(--nq-dim)] font-normal">Nhân viên</span>
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => quickLogin("lan")}
              className="p-2 text-xs font-bold font-mono uppercase border border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] bg-[var(--nq-surface-hi)] transition-colors text-left"
            >
              👔 Lan<br /><span className="text-[var(--nq-dim)] font-normal">Quản lý</span>
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => quickLogin("hung")}
              className="p-2 text-xs font-bold font-mono uppercase border border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] bg-[var(--nq-surface-hi)] transition-colors text-left"
            >
              👑 Hùng<br /><span className="text-[var(--nq-dim)] font-normal">Chủ quán</span>
            </button>
          </div>
        </div>

        {error ? <Alert kind="err">{error}</Alert> : null}

        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Tài khoản">
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="lan / minh / hung"
              className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-3 text-[var(--nq-fg)] font-mono text-base focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
            />
          </Field>

          <Field label="Mật khẩu">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="nhipquan"
              className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-3 text-[var(--nq-fg)] font-mono text-base focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
            />
          </Field>

          <div className="pt-4">
            <Btn type="submit" variant="primary" block busy={loading} busyLabel="Đang đăng nhập…">
              Vào hệ thống
            </Btn>
          </div>
        </form>
      </div>
    </main>
  );
}
