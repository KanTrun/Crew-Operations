"use client";

import { useEffect, useState } from "react";
import { getRole, type Role } from "../../lib/session";
import { AuthGate, Kicker, LinkGrid, LinkTile, PageHeader } from "../../ui/kit";

type LinkItem = { href: string; label: string; roles?: Role[] };

const LINKS: LinkItem[] = [
  { href: "/quay", label: "Quầy nội bộ", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/pha", label: "Màn hình pha chế", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/phieu", label: "Phiếu ca", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/toi", label: "Ca của tôi", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/treo", label: "Việc treo", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/doi-ca", label: "Chợ đổi ca", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/handover", label: "Bàn giao", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/hao-phi", label: "Hao phí", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/tieu-thu", label: "Sổ tiêu thụ", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/cong-bang", label: "Công bằng", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/sop", label: "Hỏi SOP", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/tkb", label: "Thời khoá biểu từ ảnh", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
  { href: "/page-quan", label: "Page quán", roles: ["quan_ly", "chu_quan"] },
  { href: "/roster", label: "Lịch tuần", roles: ["quan_ly", "chu_quan"] },
  { href: "/inbox", label: "Hộp thư", roles: ["quan_ly", "chu_quan"] },
  { href: "/cam-nang", label: "Cẩm nang", roles: ["nhan_vien", "quan_ly", "chu_quan"] },
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
