"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getToken } from "../lib/session";
import { btnGhost, btnPrimary, Kicker } from "../ui/kit";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (getToken()) router.replace("/hom-nay");
  }, [router]);

  return (
    <main ref={containerRef} className="relative min-h-[200vh] bg-[var(--nq-bg)]">
      <motion.div
        style={{ y: y1 }}
        className="pointer-events-none fixed top-[10%] left-[5%] h-[40vw] w-[40vw] rounded-full bg-[var(--nq-copper-glow)] opacity-40 blur-[120px] mix-blend-screen will-change-transform"
      />
      <motion.div
        style={{ y: y2 }}
        className="pointer-events-none fixed right-[5%] bottom-[10%] h-[50vw] w-[50vw] rounded-full bg-[var(--nq-red-dim)] opacity-20 blur-[150px] mix-blend-screen will-change-transform"
      />

      <section className="relative z-10 flex min-h-dvh flex-col items-center justify-center px-4 py-16">
        <motion.div
          style={{ opacity }}
          className="mx-auto flex w-full max-w-4xl flex-col items-center text-center will-change-opacity"
        >
          <div className="mb-10">
            <Logo />
          </div>

          <div className="hero-text mb-8 flex flex-wrap justify-center gap-x-4 gap-y-2 text-5xl font-black leading-[0.9] tracking-tighter text-[var(--nq-fg)] uppercase sm:text-7xl md:text-8xl lg:text-[9rem]">
            <span className="block">NHỊP</span>
            <span className="block text-[var(--nq-copper)]">QUÁN</span>
          </div>

          <p className="hero-desc mb-10 max-w-2xl text-lg font-medium text-[var(--nq-dim)] md:text-2xl">
            Hệ điều hành ca cho quán cà phê —{" "}
            <span className="text-[var(--nq-fg)]">tinh gọn</span> trên điện thoại,{" "}
            <span className="text-[var(--nq-fg)]">mạnh mẽ</span> trên màn lớn.
          </p>

          <div className="hero-actions flex w-full max-w-md flex-col gap-4 sm:flex-row sm:gap-6">
            <Link
              href="/login"
              className="nq-ink-on-solid flex-1 border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] px-8 py-5 text-center font-black tracking-widest uppercase transition-all duration-300 hover:bg-transparent hover:text-[var(--nq-copper)]"
            >
              Vào Ca
            </Link>
            <Link
              href="/dang-ky"
              className="flex-1 border-2 border-[var(--nq-dim)] bg-transparent px-8 py-5 text-center font-bold tracking-widest text-[var(--nq-fg)] uppercase transition-all duration-300 hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)]"
            >
              Gia Nhập
            </Link>
          </div>

          <div className="hero-scroll mt-12 flex items-center gap-4 font-mono text-sm tracking-widest text-[var(--nq-dim)] uppercase">
            <span className="h-[2px] w-12 bg-[var(--nq-dim)]" />
            Cuộn để khám phá
            <span className="h-[2px] w-12 bg-[var(--nq-dim)]" />
          </div>
        </motion.div>
      </section>

      <section className="relative z-10 mx-auto max-w-7xl px-4 py-24 md:px-12">
        <div className="grid grid-cols-1 items-center gap-16 md:grid-cols-2 md:gap-24">
          <div className="space-y-8">
            <h2 className="text-4xl font-black tracking-tighter text-[var(--nq-copper)] uppercase md:text-6xl">
              Một Việc
              <br />
              Một Lúc
            </h2>
            <p className="border-l-4 border-[var(--nq-copper)] pl-6 text-xl text-[var(--nq-dim)]">
              Không còn bảng tính rối rắm hay nhóm chat lộn xộn. Mọi thứ từ xếp ca, điểm danh đến
              kiểm kê đều nằm gọn trong một luồng công việc duy nhất.
            </p>
          </div>

          <div className="relative flex aspect-square flex-col justify-between border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-8 shadow-[16px_16px_0px_0px_var(--nq-copper-dim)]">
            <div className="font-mono text-sm tracking-widest text-[var(--nq-copper)] uppercase">
              Hệ Sinh Thái AI
            </div>
            <div className="text-4xl font-black uppercase">
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
        </div>
      </section>
    </main>
  );
}
