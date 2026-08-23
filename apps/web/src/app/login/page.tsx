"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { Alert, EditorialBanner, Field, inputStyle, Kicker } from "../../ui/kit";

type LoginOut = { token: string; role: string; display_name: string; nv_id: string };

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
      const data = await apiSend<LoginOut>("/api/v1/auth/login", { username, password });
      sessionStorage.setItem("nq_token", data.token);
      sessionStorage.setItem("nq_role", data.role);
      sessionStorage.setItem("nq_name", data.display_name);
      sessionStorage.setItem("nq_nv", data.nv_id);
      router.push("/hom-nay");
    } catch (e) {
      // 401 ở đây là sai tài khoản, không phải hết phiên — nói đúng việc.
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        setError("Tài khoản hoặc mật khẩu chưa đúng. Nhập lại, hoặc nhờ quản lý cấp lại.");
      } else {
        setError(viError(e, { doing: "vào được hệ thống" }));
      }
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
          {/* Không in tài khoản/mật khẩu mẫu ở đây: docs/design-guidelines.md —
              "Login: không in credential trên UI prod". Người triển khai tra
              runbook demo trên máy chủ, không tra màn hình đăng nhập. */}
          <p className="nq-login-hint">
            Dùng tài khoản quán do quản lý cấp. Quên mật khẩu thì nhờ quản lý đặt lại — hệ thống không
            gửi lại mật khẩu qua màn hình này.
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
