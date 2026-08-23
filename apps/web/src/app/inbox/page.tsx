"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Item = { id: string; tom_tat: string; trang_thai: string; agent: string };

export default function InboxPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const load = useCallback(() => {
    if (!token) return;
    fetch(`${API}/api/v1/inbox/rang-buoc`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => setItems(d.items ?? []));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(id: string, quyet_dinh: string) {
    await fetch(`${API}/api/v1/inbox/rang-buoc/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ quyet_dinh }),
    });
    load();
  }

  if (!token) {
    return (
      <main style={{ padding: "2rem" }}>
        <Link href="/">Đăng nhập</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "1rem" }}>
      <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Hộp thư ràng buộc</h1>
      <p style={{ fontSize: 13, color: "var(--nq-ink-muted)" }}>Người duyệt. Hệ thống không tự chọn khi VF-CONFLICT.</p>
      {items.map((it) => (
        <div key={it.id} style={{ borderBottom: "1px solid var(--nq-line)", padding: "0.75rem 0" }}>
          <p>
            {it.agent}: {it.tom_tat} · {it.trang_thai}
          </p>
          {it.trang_thai === "cho_duyet" && (
            <p>
              <button onClick={() => decide(it.id, "duyet")}>Duyệt</button>{" "}
              <button onClick={() => decide(it.id, "tu_choi")}>Từ chối</button>
            </p>
          )}
        </div>
      ))}
    </main>
  );
}
