"use client";

import { FormEvent, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import gsap from "gsap";
import { ApiError, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { Alert, Field } from "../../ui/kit";

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

  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    // Neo-brutalism entrance animation
    gsap.fromTo(
      ".nq-login-card",
      { y: 100, opacity: 0, rotate: -2 },
      { y: 0, opacity: 1, rotate: 0, duration: 0.8, ease: "back.out(1.7)" }
    );
    
    gsap.fromTo(
      ".nq-kinetic-text span",
      { y: 50, opacity: 0 },
      { y: 0, opacity: 1, stagger: 0.1, duration: 0.6, ease: "power3.out", delay: 0.2 }
    );
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" ref={containerRef}>
      {/* Abstract background elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-[var(--nq-copper-glow)] blur-[100px] opacity-50 mix-blend-screen" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-[var(--nq-red-dim)] blur-[120px] opacity-30 mix-blend-screen" />
      
      <form onSubmit={onSubmit} className="nq-login-card relative z-10 w-full max-w-[440px] bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-8 md:p-12 shadow-[16px_16px_0px_0px_var(--nq-copper-dim)] transition-transform hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[20px_20px_0px_0px_var(--nq-copper-dim)]">
        <div className="nq-login-body flex flex-col gap-6">
          <div className="nq-kinetic-text flex gap-2 overflow-hidden text-[var(--nq-copper)] font-bold uppercase tracking-widest text-sm mb-2">
            <span>Vào</span>
            <span>Ca</span>
            <span>·</span>
            <span>Một</span>
            <span>Việc</span>
            <span>Một</span>
            <span>Lúc</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-black uppercase leading-none tracking-tighter mb-4 text-[var(--nq-fg)] mix-blend-difference">
            Đăng<br/>Nhập
          </h1>
          
          <p className="text-[var(--nq-dim)] text-sm mb-4 border-l-4 border-[var(--nq-copper)] pl-4">
            Dùng tài khoản quán do quản lý cấp. Quên mật khẩu thì nhờ quản lý đặt lại — hệ thống không
            gửi lại mật khẩu qua màn hình này.
          </p>
          
          <div className="flex flex-col gap-5">
            <Field label="Tài khoản">
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>
            <Field label="Mật khẩu">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>
          </div>
          
          {error ? (
            <div className="animate-in fade-in slide-in-from-bottom-2">
              <Alert>{error}</Alert>
            </div>
          ) : null}
          
          <button 
            type="submit" 
            disabled={loading}
            className="w-full mt-4 bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-5 px-6 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Đang vào…" : "Vào hệ thống"}
          </button>
          
          <div className="mt-8 pt-6 border-t-2 border-dashed border-[var(--nq-dim)] flex flex-col gap-2 text-sm text-[var(--nq-dim)]">
            <p>Chưa có tài khoản quán? <Link href="/dang-ky" className="text-[var(--nq-copper)] hover:underline underline-offset-4 decoration-2">Tạo tài khoản nhân viên</Link></p>
            <p>Muốn biết một ngày của quán chạy thế nào? <Link href="/huong-dan" className="text-[var(--nq-copper)] hover:underline underline-offset-4 decoration-2">Đọc hướng dẫn</Link></p>
          </div>
        </div>
      </form>
    </main>
  );
}
