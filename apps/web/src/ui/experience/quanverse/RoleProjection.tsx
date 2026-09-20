"use client";

/** RoleProjection — hiển thị khoanh vùng theo vai trò (server đã strip). */

import type { ReactNode } from "react";

export type RoleId = "khach" | "nhan_vien" | "quan_ly" | "chu_quan";

const ROLE_LABEL: Record<RoleId, string> = {
  khach: "Khách",
  nhan_vien: "Nhân viên",
  quan_ly: "Quản lý",
  chu_quan: "Chủ quán",
};

interface Props {
  role: RoleId;
  children: ReactNode;
}

export default function RoleProjection({ role, children }: Props) {
  return (
    <section className="nq-role" aria-label={`Bản chiếu vai trò ${ROLE_LABEL[role]}`}>
      <header className="nq-role__head">
        <h2>{ROLE_LABEL[role]}</h2>
        <span className="nq-fixture-chip">Chế độ replay</span>
      </header>
      {children}
    </section>
  );
}