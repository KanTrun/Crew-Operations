"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HomNayPage() {
  const [token, setToken] = useState("");
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [fair, setFair] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const load = useCallback(() => {
    const t = sessionStorage.getItem("nq_token");
    if (!t) return;
    const h = { Authorization: `Bearer ${t}` };
    fetch(`${API}/api/v1/hom-nay`, { headers: h }).then((r) => r.json()).then(setData);
    fetch(`${API}/api/v1/cong-bang`, { headers: h }).then((r) => r.json()).then(setFair);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) {
    return (
      <main style={{ maxWidth: 520, margin: "0 auto", padding: "2rem 1rem" }}>
        <p>Đăng nhập với tài khoản quản lý hoặc chủ quán để xem bảng hôm nay.</p>
        <Link href="/">Về trang chủ</Link>
      </main>
    );
  }

  const life = (data?.lich as { trang_thai?: string; nguon?: string }) || {};
  const means = (fair?.means as Record<string, number>) || {};

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "1rem" }}>
      <p style={{ letterSpacing: "0.2em", textTransform: "uppercase", fontSize: 12, color: "var(--nq-ink-muted)" }}>
        Ca hôm nay
      </p>
      <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Quán hôm nay</h1>
      <p>Lịch: {life.trang_thai ?? "…"} · nguồn {life.nguon}</p>
      <p>Cảnh báo tồn: {(data?.canh_bao_ton as string[] | undefined)?.join(", ")}</p>
      <h2 style={{ fontSize: "1.1rem" }}>Công bằng (so với trung bình nhóm, không xếp hạng tên)</h2>
      <ul>
        {Object.entries(means).map(([k, v]) => (
          <li key={k} style={{ fontFamily: "var(--nq-font-mono)" }}>
            {k}: {Number(v).toFixed(2)}
          </li>
        ))}
      </ul>
      <p>
        <Link href="/cong-bang">Bảng công bằng đầy đủ</Link> · <Link href="/">Home</Link>
      </p>
    </main>
  );
}
