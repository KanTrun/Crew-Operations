"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { getToken, isManager } from "../../lib/session";
import {
  AuthGate,
  Btn,
  BtnLink,
  InlineActions,
  LinkGrid,
  LinkTile,
  Loading,
  OpsCard,
  PageHeader,
} from "../../ui/kit";
import { chayLaiTour } from "../../ui/tour";

const LINKS: Array<[string, string]> = [
  ["/cong-bang", "Xem công bằng"],
  ["/doi-ca", "Đổi ca"],
  ["/qr", "Điểm danh QR"],
  ["/tieu-thu", "Ghi sổ tiêu thụ"],
  ["/hao-phi", "Ghi hao phí"],
  ["/sop", "Hỏi SOP"],
  ["/handover", "Bàn giao ca"],
  ["/vet", "Đọc vết hệ thống"],
  ["/phieu", "Mở phiếu ca"],
  ["/toi", "Ca của tôi"],
  ["/treo", "Việc treo"],
  ["/roster", "Xếp lịch tuần"],
  ["/inbox", "Duyệt hộp thư"],
  ["/cam-nang", "Đọc cẩm nang"],
];

export default function ThemPage() {
  const [token, setToken] = useState("");
  const [ready, setReady] = useState(false);
  const [daBo, setDaBo] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setToken(getToken());
    setReady(true);
  }, []);

  useEffect(() => {
    if (containerRef.current && ready) {
      gsap.fromTo(
        ".ops-animate-in",
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, stagger: 0.1, duration: 0.5, ease: "power2.out" }
      );
    }
  }, [ready]);

  /**
   * "Bỏ qua hẳn" ghi dấu đã xem mà không mở tour: người đã biết việc không phải
   * mở lớp phủ lên rồi bấm Bỏ qua chỉ để nó im.
   */
  function boQua() {
    try {
      localStorage.setItem("nq_onboarding_v1", "1");
      setDaBo(true);
    } catch {
      setDaBo(false);
    }
  }

  if (!ready) {
    return (
      <div className="min-h-screen p-4 md:p-8 flex items-center justify-center">
        <Loading skeleton="list">Đang mở danh sách việc…</Loading>
      </div>
    );
  }
  if (!token) return <AuthGate />;
  const manager = isManager();

  return (
    <main className="min-h-screen p-4 md:p-8 pb-32 relative" ref={containerRef}>
      <header className="mb-12 ops-animate-in">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          Thêm
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm max-w-2xl">
          Mọi việc còn lại của quán, gom một chỗ — bạn đang vào với vai <span className="text-[var(--nq-copper)]">{manager ? "quản lý hoặc chủ quán" : "nhân viên"}</span>.
        </p>
      </header>

      <div className="ops-animate-in mb-12">
        <div className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-copper)] p-6 md:p-8 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
          <h2 className="text-2xl font-black uppercase mb-4 text-[var(--nq-fg)]">Hướng dẫn từng vùng</h2>
          <p className="text-[var(--nq-dim)] font-mono text-sm mb-8 max-w-3xl">
            Lớp hướng dẫn chạy một lần khi bạn vào lần đầu, chỉ vào từng vùng trên bảng Hôm nay và nói
            vùng đó để làm gì. Mỗi bước có câu hỏi bấm được, bấm là sang Hỏi SOP với câu đã điền —
            câu trả lời lấy từ mẫu phiếu và luật của quán, kèm trích dẫn.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <button 
              type="button"
              onClick={chayLaiTour}
              className="flex-1 bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-4 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)]"
            >
              Xem lại hướng dẫn
            </button>
            <button 
              type="button"
              onClick={boQua}
              className="flex-1 bg-transparent text-[var(--nq-dim)] font-bold uppercase tracking-widest py-4 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-fg)] hover:text-[var(--nq-fg)] transition-all"
            >
              Bỏ qua, đừng hiện nữa
            </button>
            <BtnLink href="/huong-dan" className="flex-1 bg-transparent text-[var(--nq-dim)] font-bold uppercase tracking-widest py-4 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all text-center">
              Đọc một ngày của quán
            </BtnLink>
          </div>
          {daBo ? (
            <p className="text-[var(--nq-green)] font-mono text-sm mt-6 border-l-4 border-[var(--nq-green)] pl-4">
              Đã tắt lớp hướng dẫn. Bấm “Xem lại hướng dẫn” bất cứ lúc nào để mở lại.
            </p>
          ) : null}
        </div>
      </div>

      <div className="ops-animate-in">
        <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
          Việc còn lại của quán
          <span className="text-sm bg-[var(--nq-copper)] text-[#0e0c0a] px-3 py-1 rounded-full">{LINKS.length}</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {LINKS.map(([href, label]) => (
            <LinkTile key={href} href={href} className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all group hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[4px_4px_0px_0px_var(--nq-copper-dim)]">
              <span className="font-bold uppercase tracking-widest text-sm group-hover:text-[var(--nq-copper)] text-[var(--nq-fg)] transition-colors">{label}</span>
            </LinkTile>
          ))}
        </div>
      </div>
    </main>
  );
}
