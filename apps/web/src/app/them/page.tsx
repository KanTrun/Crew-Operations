"use client";

import { useEffect, useState } from "react";
import { getRole, type Role } from "../../lib/session";
import { AuthGate, Kicker, LinkGrid, LinkTile, PageHeader } from "../../ui/kit";

type LinkItem = { href: string; label: string; roles?: Role[] };

const LINKS: LinkItem[] = [
  { href: "/quay", label: "Quầy nội bộ" },
  { href: "/pha", label: "Màn hình pha chế" },
  { href: "/phieu", label: "Phiếu ca" },
  { href: "/toi", label: "Ca của tôi" },
  { href: "/treo", label: "Việc treo" },
  { href: "/doi-ca", label: "Chợ đổi ca" },
  { href: "/handover", label: "Bàn giao" },
  { href: "/hao-phi", label: "Hao phí" },
  { href: "/tieu-thu", label: "Sổ tiêu thụ" },
  { href: "/cong-bang", label: "Công bằng" },
  { href: "/sop", label: "Hỏi SOP" },
  { href: "/tkb", label: "Thời khoá biểu từ ảnh" },
  { href: "/page-quan", label: "Page quán" },
  { href: "/roster", label: "Lịch tuần", roles: ["quan_ly", "chu_quan"] },
  { href: "/inbox", label: "Hộp thư", roles: ["quan_ly", "chu_quan"] },
  { href: "/cam-nang", label: "Cẩm nang", roles: ["quan_ly", "chu_quan"] },
  { href: "/menu", label: "Menu & giá", roles: ["chu_quan"] },
  { href: "/nguoi", label: "Người dùng", roles: ["chu_quan"] },
  { href: "/vet", label: "Vết hệ thống", roles: ["chu_quan"] },
];

export default function ThemPage() {
  const [role, setRole] = useState<Role>("");

  useEffect(() => setRole(getRole()), []);
  if (!role) return <AuthGate />;
  const visible = LINKS.filter((item) => !item.roles || item.roles.includes(role));

  return (
    <section className="nq-page">
      <Kicker>Lối tắt theo vai trò</Kicker>
      <PageHeader
        kicker="Thêm"
        title="Việc của quán"
        meta="Các mục không thuộc quyền của bạn được ẩn tại đây và chặn cả khi gõ trực tiếp đường dẫn."
      />
      <LinkGrid>
        {visible.map((item) => (
          <LinkTile key={item.href} href={item.href}>
            {item.label}
          </LinkTile>
        ))}
      </LinkGrid>
    </section>
  );
}
