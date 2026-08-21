"use client";

import { FormEvent, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("quanly");
  const [password, setPassword] = useState("demo");
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
        setError("Sai thông tin đăng nhập (thử quanly / demo).");
        return;
      }
      const data = (await res.json()) as { token: string; role: string; display_name: string };
      sessionStorage.setItem("nq_token", data.token);
      sessionStorage.setItem("nq_role", data.role);
      sessionStorage.setItem("nq_name", data.display_name);
      router.push("/contracts");
    } catch {
      setError("Không kết nối được API. Chạy make demo / docker compose.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: "1.5rem" }}>
      <form
        onSubmit={onSubmit}
        style={{
          width: "100%",
          maxWidth: 400,
          borderTop: "1px solid var(--nq-line)",
          paddingTop: "1.5rem",
        }}
      >
        <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, marginTop: 0 }}>
          Đăng nhập
        </h1>
        <p style={{ color: "var(--nq-ink-muted)", fontSize: "0.95rem" }}>
          Fixture: <code style={{ fontFamily: "var(--nq-font-mono)" }}>quanly</code> /{" "}
          <code style={{ fontFamily: "var(--nq-font-mono)" }}>demo</code>
        </p>
        <label style={{ display: "block", marginBottom: "0.75rem" }}>
          <span style={{ display: "block", marginBottom: 6 }}>Tài khoản</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            style={inputStyle}
          />
        </label>
        <label style={{ display: "block", marginBottom: "1rem" }}>
          <span style={{ display: "block", marginBottom: 6 }}>Mật khẩu</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            style={inputStyle}
          />
        </label>
        {error ? (
          <p role="alert" style={{ color: "var(--nq-danger)" }}>
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={loading} style={btnStyle}>
          {loading ? "Đang vào…" : "Vào hệ thống"}
        </button>
      </form>
    </main>
  );
}

const inputStyle: CSSProperties = {
  width: "100%",
  minHeight: 44,
  padding: "0.6rem 0.75rem",
  background: "var(--nq-bg-elevated)",
  border: "1px solid var(--nq-line)",
  color: "var(--nq-ink)",
  borderRadius: 2,
  fontFamily: "var(--nq-font-body)",
};

const btnStyle: CSSProperties = {
  width: "100%",
  minHeight: 44,
  marginTop: "0.5rem",
  background: "var(--nq-accent)",
  color: "var(--nq-accent-ink)",
  border: "none",
  fontWeight: 600,
  borderRadius: 2,
  cursor: "pointer",
};
