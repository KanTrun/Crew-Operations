"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "../../lib/api";
import { Alert, EditorialBanner, Field, inputStyle, Kicker } from "../../ui/kit";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
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
      setError("Không kết nối được máy chủ. Chạy API rồi thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="nq-login-wrap">
      <form onSubmit={onSubmit} className="nq-login-card">
        <EditorialBanner
          status="Vào ca · một việc một lúc"
          meta="Phiếu · lịch · công bằng · cẩm nang"
        />
        <div className="nq-login-body">
          <Kicker>Vận hành ca</Kicker>
          <h1>Đăng nhập</h1>
          <p className="nq-login-hint">
            Dùng tài khoản quán được quản lý cấp. Hướng dẫn demo nằm trong{" "}
            <code style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.78rem" }}>docs/runbook-demo.md</code>{" "}
            trên máy chủ triển khai.
          </p>
          <Field label="Tài khoản">
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              style={inputStyle}
            />
          </Field>
          <Field label="Mật khẩu">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              style={inputStyle}
            />
          </Field>
          {error ? <Alert>{error}</Alert> : null}
          <button type="submit" disabled={loading} className="nq-btn nq-btn-primary nq-btn-block">
            {loading ? "Đang vào…" : "Vào hệ thống"}
          </button>
        </div>
      </form>
    </main>
  );
}
