"use client";

import { useEffect, useState } from "react";
import { getToken, isManager } from "../../lib/session";
import { AuthGate, Empty, LinkGrid, LinkTile, Loading, PageHeader } from "../../ui/kit";

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
  useEffect(() => {
    setToken(getToken());
    setReady(true);
  }, []);
  if (!ready) {
    return (
      <div className="nq-page">
        <Loading skeleton="list">Đang mở danh sách việc…</Loading>
      </div>
    );
  }
  if (!token) return <AuthGate />;
  const manager = isManager();
  return (
    <div className="nq-page">
      <PageHeader
        kicker="Tất cả mặt"
        title="Thêm"
        meta={`Mọi việc còn lại của quán, gom một chỗ — bạn đang vào với vai ${
          manager ? "quản lý hoặc chủ quán" : "nhân viên"
        }.`}
      />
      {LINKS.length === 0 ? (
        <Empty>Chưa có lối tắt nào.</Empty>
      ) : (
        <LinkGrid>
          {LINKS.map(([href, label]) => (
            <LinkTile key={href} href={href}>
              {label}
            </LinkTile>
          ))}
        </LinkGrid>
      )}
    </div>
  );
}
