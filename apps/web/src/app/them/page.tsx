"use client";

import { useEffect, useState } from "react";
import { getToken, isManager } from "../../lib/session";
import { AuthGate, BtnLink, LinkGrid, LinkTile, OpsCard, PageHeader } from "../../ui/kit";
import { chayLaiTour } from "../../ui/tour";

const LINKS: Array<[string, string]> = [
  ["/huong-dan", "Bản đồ hướng dẫn"],
  ["/tkb", "Thời khoá biểu từ ảnh"],
  ["/cong-bang", "Xem công bằng"],
  ["/page-quan", "Page quán"],
  ["/doi-ca", "Đổi ca"],
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
        kicker="Menu phụ"
        title="Thêm"
        meta={
          <>
            Mọi việc còn lại của quán — vai{" "}
            <strong>{manager ? "quản lý hoặc chủ quán" : "nhân viên"}</strong>.
          </>
        }
      />

      <OpsCard eyebrow="Hướng dẫn" title="Bản đồ & tour">
        <p className="nq-muted mb-6">
          Đọc bản đồ tương tác để hiểu liên kết giữa các trang từ đầu tới cuối.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <BtnLink href="/huong-dan" variant="primary">
            Mở bản đồ NHỊP QUÁN
          </BtnLink>
          <button type="button" className="nq-filter-clear" onClick={() => chayLaiTour()}>
            Xem lại tour (sắp có)
          </button>
        </div>
      </OpsCard>

      <OpsCard eyebrow="Danh mục" title="Việc còn lại" count={LINKS.length} countLabel="liên kết">
        <LinkGrid>
          {LINKS.map(([href, label]) => (
            <LinkTile key={href} href={href}>
              {label}
            </LinkTile>
          ))}
        </LinkGrid>
      </OpsCard>
    </div>
  );
}
