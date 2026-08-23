"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "../../lib/api";
import { btnPrimary, Field, inputStyle, Alert, Kicker } from "../../ui/kit";

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
    <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: "1.5rem" }}>
      <form onSubmit={onSubmit} style={{ width: "100%", maxWidth: 400 }}>
        <Kicker>Vận hành ca</Kicker>
        <h1>Đăng nhập</h1>
        <p className="nq-muted" style={{ marginBottom: "1.25rem" }}>
          Tài khoản quán: lan, minh, hung — mật khẩu nhipquan.
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
        <button type="submit" disabled={loading} style={{ ...btnPrimary, width: "100%" }}>
          {loading ? "Đang vào…" : "Vào hệ thống"}
        </button>
      </form>
    </main>
  );
}
