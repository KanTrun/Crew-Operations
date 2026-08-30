"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiSend } from "../../lib/api";
import { setSession } from "../../lib/session";
import { viError } from "../../lib/present";
import { Alert, Field, Input } from "../../ui/kit";
import { Logo } from "../../ui/Logo";

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
      setSession(data.token, data.role, data.display_name, data.nv_id);
      router.push("/hom-nay");
    } catch (e) {
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
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden p-4 md:p-8">
      <div className="pointer-events-none absolute top-[-10%] left-[-10%] h-[40vw] w-[40vw] rounded-full bg-[var(--nq-copper-glow)] opacity-40 blur-[100px] mix-blend-screen" />
      <div className="pointer-events-none absolute right-[-10%] bottom-[-10%] h-[35vw] w-[35vw] rounded-full bg-[var(--nq-red-dim)] opacity-25 blur-[120px] mix-blend-screen" />

      <form
        onSubmit={onSubmit}
        className="nq-login-card relative z-10 grid w-full max-w-4xl grid-cols-1 overflow-hidden border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] md:grid-cols-2"
      >
        <aside className="flex flex-col justify-between border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-6 md:border-r-2 md:border-b-0 md:p-8">
          <Logo />
          <div className="mt-8 md:mt-0">
            <p className="mb-2 font-mono text-xs tracking-widest text-[var(--nq-copper)] uppercase">
              Vào ca · một việc một lúc
            </p>
            <h1 className="text-4xl font-black tracking-tighter text-[var(--nq-fg)] uppercase md:text-5xl">
              Đăng nhập
            </h1>
            <p className="mt-4 max-w-sm text-sm text-[var(--nq-dim)]">
              Dùng tài khoản quán do quản lý cấp. Quên mật khẩu thì nhờ quản lý đặt lại.
            </p>
          </div>
          <p className="mt-8 hidden text-xs font-mono text-[var(--nq-dim)] md:block">
            NHỊP QUÁN · Digital System
          </p>
        </aside>

        <div className="flex flex-col gap-4 p-6 md:gap-5 md:p-8">
          <Field label="Tài khoản">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="font-mono"
            />
          </Field>
          <Field label="Mật khẩu">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="font-mono"
            />
          </Field>

          {error ? <Alert>{error}</Alert> : null}

          <button
            type="submit"
            disabled={loading}
            aria-busy={loading ? true : undefined}
            className="nq-ink-on-solid mt-2 w-full border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] py-3.5 font-black tracking-widest uppercase transition-all hover:bg-transparent hover:text-[var(--nq-copper)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Đang vào…" : "Vào hệ thống"}
          </button>

          <div className="mt-2 space-y-1 border-t-2 border-dashed border-[var(--nq-dim)] pt-4 text-sm text-[var(--nq-dim)]">
            <p>
              Chưa có tài khoản?{" "}
              <Link href="/dang-ky" className="text-[var(--nq-copper)] underline-offset-4 hover:underline">
                Tạo tài khoản nhân viên
              </Link>
            </p>
            <p>
              <Link href="/huong-dan" className="text-[var(--nq-copper)] underline-offset-4 hover:underline">
                Đọc bản đồ hướng dẫn từ đầu tới cuối
              </Link>
            </p>
          </div>
        </div>
      </form>
    </main>
  );
}
