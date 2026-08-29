"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getToken } from "../lib/session";
import { BentoTile, BtnLink, EditorialBanner, Kicker } from "../ui/kit";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (getToken()) router.replace("/hom-nay");
  }, [router]);

  return (
    <div className="relative z-10 min-h-screen p-4 sm:p-8 md:p-12 max-w-6xl mx-auto">
      <EditorialBanner
        wordmark="NHỊP QUÁN"
        status="Hệ thống vận hành quán 3 vai"
        meta="Vận hành ca liền mạch · Quầy POS & KDS nội bộ · Xếp lịch & Cẩm nang sống"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <BentoTile
          label="Vỏ Nhân viên"
          value="minh"
          accent="default"
          href="/login"
        />
        <BentoTile
          label="Vỏ Quản lý"
          value="lan"
          accent="warn"
          href="/login"
        />
        <BentoTile
          label="Vỏ Chủ quán"
          value="hung"
          accent="ok"
          href="/login"
        />
      </div>

      <div className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 sm:p-10 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
        <Kicker>Một việc tại một thời điểm</Kicker>
        <h2 className="text-2xl sm:text-3xl font-black uppercase text-[var(--nq-fg)] mb-4">
          Bắt đầu phiên làm việc
        </h2>
        <p className="text-[var(--nq-dim)] font-mono text-sm mb-8 max-w-2xl">
          Đăng nhập bằng tài khoản vai trò của bạn để truy cập đúng các chức năng được phân quyền (quầy POS, màn hình pha chế KDS, phiếu mở/đóng ca, lịch tuần hoặc quản trị menu).
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <BtnLink href="/login" variant="primary">
            Đăng nhập ngay
          </BtnLink>
        </div>
      </div>
    </div>
  );
}
