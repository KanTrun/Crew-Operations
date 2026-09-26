"use client";

/** RoleProjection — khoanh vùng theo vai trò (server đã strip) + tóm tắt phạm vi. */

import type { ReactNode } from "react";
import { Icon, type IconName } from "../../icons";
import { RoleChip } from "../exp-kit";

export type RoleId = "khach" | "nhan_vien" | "quan_ly" | "chu_quan";

export const ROLE_LABEL: Record<RoleId, string> = {
  khach: "Khách",
  nhan_vien: "Nhân viên",
  quan_ly: "Quản lý",
  chu_quan: "Chủ quán",
};

const ROLE_ICON: Record<RoleId, IconName> = {
  khach: "coffee",
  nhan_vien: "users",
  quan_ly: "roster",
  chu_quan: "cong-bang",
};

/**
 * Mỗi vai trò nhìn thấy một phần khác nhau của cùng một quán. Nói rõ phần nào
 * bị ẩn để người dùng không tưởng dữ liệu "biến mất" mà là bị giới hạn quyền.
 */
const ROLE_SCOPE: Record<RoleId, string> = {
  khach: "Chỉ khu vực dành cho khách — không có dữ liệu vận hành và ký ức nội bộ.",
  nhan_vien: "Toàn mặt bằng, ca cứu và tín hiệu — không có ký ức riêng của khách.",
  quan_ly: "Toàn mặt bằng, sự kiện vận hành, chế độ quán và đề xuất cần duyệt.",
  chu_quan: "Toàn quyền: vận hành, công bằng, cấu hình và ký ức quán.",
};

interface Props {
  role: RoleId;
  children: ReactNode;
}

export default function RoleProjection({ role, children }: Props) {
  return (
    <section className="nq-role" aria-label={`Bản chiếu vai trò ${ROLE_LABEL[role]}`}>
      <header className="nq-role__head">
        <span className="nq-role__glyph" aria-hidden="true">
          <Icon name={ROLE_ICON[role]} size={18} />
        </span>
        <h2>{ROLE_LABEL[role]}</h2>
        <p className="nq-role__scope">{ROLE_SCOPE[role]}</p>
        <RoleChip label="Bản chiếu trực tiếp" />
      </header>
      {children}
    </section>
  );
}