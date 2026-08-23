"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getToken } from "../lib/session";
import { BtnLink, EditorialBanner, Kicker, PageActions } from "../ui/kit";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (getToken()) router.replace("/hom-nay");
  }, [router]);

  return (
    <>
      <EditorialBanner
        status="OS vận hành ca · đêm quán sống"
        meta="Một việc một lúc — phiếu, lịch, công bằng"
      />
      <div className="nq-page nq-page--home">
        <Kicker>OS vận hành ca</Kicker>
        <h1>NHỊP QUÁN</h1>
        <p className="nq-muted" style={{ maxWidth: 520, fontSize: "1.05rem" }}>
          Hệ điều hành ca cho quán cà phê — tinh gọn trên điện thoại, rộng rãi trên màn lớn. Đăng nhập
          để vào bảng hôm nay.
        </p>
        <PageActions>
          <BtnLink href="/login">Đăng nhập vào ca</BtnLink>
        </PageActions>
        <p className="nq-muted" style={{ maxWidth: 520, fontSize: "0.85rem", marginTop: "1rem" }}>
          Chưa có tài khoản quán? Nhờ quản lý cấp. Cách dựng quán và tài khoản nằm trong runbook
          triển khai, không in trên màn hình này.
        </p>
      </div>
    </>
  );
}
