"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Luat = {
  id: string;
  cau: string;
  trang_thai: string;
  tap_su_dung?: number;
  ap_dung?: number;
  ghi_de?: number;
  vf_rule?: string;
  bang_chung?: string[];
};

export default function CamNangPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Luat[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const load = useCallback(() => {
    fetch(`${API}/api/v1/cam-nang`)
      .then((r) => r.json())
      .then((d) => setItems(d.items ?? []));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function chay() {
    const r = await fetch(`${API}/api/v1/cam-nang/chay-8-buoc`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    const d = await r.json();
    setMsg(
      r.ok
        ? `Luật đã hiệu lực. VF-RULE loại: ${d.bi_loai?.vf_rule}. Luật từ người quán ngoài: ${d.so_luat_that_quan}.`
        : "Không chạy được (cần quyền quản lý).",
    );
    load();
  }

  if (!token) {
    return (
      <main style={{ maxWidth: 520, margin: "0 auto", padding: "2rem 1rem" }}>
        <p>Đăng nhập quản lý/chủ.</p>
        <Link href="/">Home</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "1rem" }}>
      <p style={{ fontSize: 12, color: "var(--nq-ink-muted)" }}>Cẩm nang sống</p>
      <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Cẩm nang quán</h1>
      <button
        onClick={chay}
        style={{
          minHeight: 44,
          background: "var(--nq-accent)",
          color: "var(--nq-accent-ink)",
          border: 0,
          padding: "0.5rem 1rem",
          marginBottom: 16,
        }}
      >
        Chạy 8 bước
      </button>
      {msg && <p>{msg}</p>}
      {items.map((it) => (
        <article
          key={it.id}
          style={{ border: "1px solid var(--nq-line)", borderRadius: 8, padding: "1rem", marginBottom: 12 }}
        >
          <p style={{ fontWeight: 600 }}>{it.cau}</p>
          <p>
            Trạng thái: {it.trang_thai} {it.vf_rule ? `· VF-RULE: ${it.vf_rule}` : ""}
          </p>
          <p>
            Nguồn: {(it.bang_chung || []).length} lần sửa · Tập sự: {it.tap_su_dung ?? "—"} · Áp dụng {it.ap_dung ?? 0}{" "}
            · Ghi đè {it.ghi_de ?? 0}
          </p>
        </article>
      ))}
      <Link href="/sop">Hỏi SOP →</Link>
    </main>
  );
}
