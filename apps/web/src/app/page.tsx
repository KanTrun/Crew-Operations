"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import gsap from "gsap";
import { getToken } from "../lib/session";
import { Logo } from "../ui/Logo";

export default function HomePage() {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"]
  });

  const y1 = useTransform(scrollYProgress, [0, 1], [0, 200]);
  const y2 = useTransform(scrollYProgress, [0, 1], [0, -200]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  useEffect(() => {
    if (getToken()) router.replace("/hom-nay");
    
    // Initial reveal animation
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".hero-text span",
        { y: 100, opacity: 0 },
        { y: 0, opacity: 1, stagger: 0.1, duration: 1, ease: "power4.out", delay: 0.2 }
      );
      
      gsap.fromTo(
        ".hero-desc",
        { y: 50, opacity: 0 },
        { y: 0, opacity: 1, duration: 1, ease: "power3.out", delay: 0.8 }
      );
      
      gsap.fromTo(
        ".hero-actions",
        { y: 50, opacity: 0 },
        { y: 0, opacity: 1, duration: 1, ease: "power3.out", delay: 1 }
      );
    }, containerRef);
    
    return () => ctx.revert();
  }, [router]);

  return (
    <main ref={containerRef} className="min-h-[200vh] relative bg-[var(--nq-bg)] overflow-hidden">
      {/* 3D/Abstract Background Elements */}
      <motion.div 
        style={{ y: y1 }}
        className="fixed top-[10%] left-[5%] w-[40vw] h-[40vw] rounded-full bg-[var(--nq-copper-glow)] blur-[120px] opacity-40 mix-blend-screen pointer-events-none will-change-transform"
      />
      <motion.div 
        style={{ y: y2 }}
        className="fixed bottom-[10%] right-[5%] w-[50vw] h-[50vw] rounded-full bg-[var(--nq-red-dim)] blur-[150px] opacity-20 mix-blend-screen pointer-events-none will-change-transform"
      />

      {/* Hero Section */}
      <section className="h-screen flex flex-col items-center justify-center p-4 relative z-10">
        <motion.div style={{ opacity }} className="text-center flex flex-col items-center max-w-4xl mx-auto will-change-opacity">
          <div className="mb-12">
            <Logo className="scale-150 transform origin-center" />
          </div>
          
          <div className="hero-text flex flex-wrap justify-center gap-x-4 gap-y-2 text-6xl md:text-8xl lg:text-[10rem] font-black uppercase leading-[0.85] tracking-tighter text-[var(--nq-fg)] mix-blend-difference mb-8">
            <span className="block">NHỊP</span>
            <span className="block text-[var(--nq-copper)]">QUÁN</span>
          </div>
          
          <div className="hero-desc text-xl md:text-2xl text-[var(--nq-dim)] max-w-2xl text-center mb-12 font-medium">
            Hệ điều hành ca cho quán cà phê — <span className="text-[var(--nq-fg)]">tinh gọn</span> trên điện thoại, <span className="text-[var(--nq-fg)]">mạnh mẽ</span> trên màn lớn.
          </div>
          
          <div className="hero-actions flex flex-col sm:flex-row gap-6 w-full max-w-md">
            <Link 
              href="/login"
              className="flex-1 bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-5 px-8 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all duration-300 text-center"
            >
              Vào Ca
            </Link>
            <Link 
              href="/dang-ky"
              className="flex-1 bg-transparent text-[var(--nq-fg)] font-bold uppercase tracking-widest py-5 px-8 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all duration-300 text-center"
            >
              Gia Nhập
            </Link>
          </div>
          
          <div className="mt-12 text-sm text-[var(--nq-dim)] font-mono uppercase tracking-widest flex gap-4 items-center">
            <span className="w-12 h-[2px] bg-[var(--nq-dim)]" />
            Cuộn để khám phá
            <span className="w-12 h-[2px] bg-[var(--nq-dim)]" />
          </div>
        </motion.div>
      </section>

      {/* Scrollytelling Section */}
      <section className="min-h-screen relative z-10 py-24 px-4 md:px-12 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-24 items-center">
          <div className="space-y-8">
            <h2 className="text-4xl md:text-6xl font-black uppercase tracking-tighter text-[var(--nq-copper)]">
              Một Việc<br/>Một Lúc
            </h2>
            <p className="text-xl text-[var(--nq-dim)] border-l-4 border-[var(--nq-copper)] pl-6">
              Không còn bảng tính rối rắm hay nhóm chat lộn xộn. Mọi thứ từ xếp ca, điểm danh đến kiểm kê đều nằm gọn trong một luồng công việc duy nhất.
            </p>
          </div>
          
          <div className="relative aspect-square bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-8 shadow-[16px_16px_0px_0px_var(--nq-copper-dim)] flex flex-col justify-between">
            <div className="text-[var(--nq-copper)] font-mono uppercase tracking-widest text-sm">Hệ Sinh Thái AI</div>
            <div className="text-4xl font-black uppercase">9 Agent<br/>Chuyên<br/>Trách</div>
            <div className="text-[var(--nq-dim)]">Tự động hoá vận hành, đẩy ngoại lệ lên cho con người.</div>
          </div>
        </div>
      </section>
    </main>
  );
}
