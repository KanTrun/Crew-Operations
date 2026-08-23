"use client";

import { useEffect, useState } from "react";
import { getToken, isManager } from "../../lib/session";
import { AuthGate, LinkGrid, LinkTile, PageHeader } from "../../ui/kit";

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
      <PageHeader
        kicker="Tất cả mặt"
        title="Thêm"
        meta={`${manager ? "Quản lý / chủ quán" : "Nhân viên"} — chọn một việc.`}
      />
      <LinkGrid>
        {LINKS.map(([href, label]) => (
          <LinkTile key={href} href={href}>
            {label}
          </LinkTile>
        ))}
      </LinkGrid>
    </div>
  );
}
