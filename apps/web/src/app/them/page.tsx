"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../lib/session";
import { AuthGate, Kicker } from "../../ui/kit";

const LINKS = [
  ["/cong-bang", "Công bằng"],
  ["/doi-ca", "Chợ đổi ca"],
  ["/qr", "Điểm danh QR"],
  ["/tieu-thu", "Sổ tiêu thụ"],
  ["/hao-phi", "Hao phí"],
  ["/sop", "Hỏi SOP"],
  ["/handover", "Bàn giao"],
  ["/vet", "Vết hệ thống"],
  ["/phieu", "Phiếu"],
  ["/toi", "Ca của tôi"],
  ["/treo", "Việc treo"],
  ["/roster", "Lịch tuần"],
  ["/inbox", "Hộp thư"],
  ["/cam-nang", "Cẩm nang"],
];

export default function ThemPage() {
  const [token, setToken] = useState("");
  useEffect(() => {
    setToken(getToken());
  }, []);
  if (!token) return <AuthGate />;
  const manager = isManager();
  return (
    <div className="nq-page">
      <Kicker>Tất cả mặt</Kicker>
      <h1>Thêm</h1>
      <p className="nq-muted">{manager ? "Quản lý / chủ quán" : "Nhân viên"} — chọn một việc.</p>
      <div className="nq-list" style={{ marginTop: "1rem" }}>
        {LINKS.map(([href, label]) => (
          <Link key={href} href={href} className="nq-item" style={{ textDecoration: "none", color: "var(--nq-ink)" }}>
            {label}
          </Link>
        ))}
      </div>
    </div>
  );
}
