"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../lib/session";
import { Kicker } from "../../ui/kit";

const STAFF_MORE = [
  ["/cong-bang", "Công bằng"],
  ["/doi-ca", "Chợ đổi ca"],
  ["/qr", "QR"],
  ["/tieu-thu", "Tiêu thụ"],
  ["/hao-phi", "Hao phí"],
  ["/sop", "SOP"],
  ["/handover", "Bàn giao"],
  ["/vet", "Vết"],
] as const;

const MANAGER_MORE = [
  ["/cong-bang", "Công bằng"],
  ["/doi-ca", "Chợ đổi ca"],
  ["/phieu", "Phiếu"],
  ["/toi", "Ca của tôi"],
  ["/treo", "Việc treo"],
  ["/qr", "QR"],
  ["/tieu-thu", "Tiêu thụ"],
  ["/hao-phi", "Hao phí"],
  ["/sop", "SOP"],
  ["/handover", "Bàn giao"],
  ["/vet", "Vết"],
] as const;

export default function ThemPage() {
  const path = usePathname();
  const [token, setToken] = useState("");
  useEffect(() => setToken(getToken()), []);
  const manager = isManager();
  const links = manager ? MANAGER_MORE : STAFF_MORE;

  if (!token) {
    return (
      <div className="nq-page">
        <Kicker>Menu</Kicker>
        <h1>Thêm</h1>
        <p className="nq-muted">Đăng nhập để xem lối tắt.</p>
      </div>
    );
  }

  return (
    <div className="nq-page">
      <Kicker>Menu</Kicker>
      <h1>Thêm</h1>
      <div className="nq-list" style={{ marginTop: "1rem" }}>
        {links.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            className="nq-item"
            style={{
              textDecoration: "none",
              color: "var(--nq-ink)",
              borderColor: path === href ? "var(--nq-accent-soft)" : undefined,
            }}
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  );
}
