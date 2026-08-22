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
    <div className="nq-page">
      <Kicker>OS vận hành ca</Kicker>
      <h1>NHỊP QUÁN</h1>
      <p className="nq-muted" style={{ maxWidth: 440 }}>
        Một việc tại một thời điểm: phiếu, ca, việc treo, công bằng, cẩm nang.
        Đăng nhập để vào bảng hôm nay — không còn danh sách liên kết rời.
      </p>
      <p style={{ display: "flex", gap: "0.65rem", marginTop: "1.5rem", flexWrap: "wrap" }}>
        <Link href="/login" style={btnPrimary}>
          Đăng nhập
        </Link>
        <Link href="/login" style={btnGhost}>
          Xem hướng dẫn vào ca
        </Link>
      </p>
    </div>
  );
}
