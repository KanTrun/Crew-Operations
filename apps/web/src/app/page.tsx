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
        status="OS vận hành ca · một việc một lúc"
        meta="Phiếu · lịch · việc treo · công bằng · cẩm nang"
      />
      <div className="nq-page">
        <Kicker>OS vận hành ca</Kicker>
        <h1>NHỊP QUÁN</h1>
        <p className="nq-muted" style={{ maxWidth: 440 }}>
          Một việc tại một thời điểm. Đăng nhập để vào bảng hôm nay — không còn danh sách liên kết rời.
        </p>
        <PageActions>
          <BtnLink href="/login">Đăng nhập</BtnLink>
          <BtnLink href="/login" variant="ghost">
            Hướng dẫn vào ca
          </BtnLink>
        </PageActions>
      </div>
    </>
  );
}
