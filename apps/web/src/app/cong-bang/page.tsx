"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Debt = Record<string, Record<string, number>>;

export default function CongBangPage() {
  const [soDu, setSoDu] = useState<Debt>({});
  const [means, setMeans] = useState<Record<string, number>>({});
  const [me, setMe] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = sessionStorage.getItem("nq_token");
    const nv = sessionStorage.getItem("nq_nv") ?? "";
    setMe(nv);
    if (!token) {
      setError("Cần đăng nhập.");
      return;
    }
    fetch(`${API}/api/v1/cong-bang`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("khong_doc_duoc");
        return r.json();
      })
      .then((d) => {
        setSoDu(d.so_du ?? {});
        setMeans(d.means ?? {});
        if (d.nv_id) setMe(d.nv_id);
      })
      .catch(() => setError("Không đọc được sổ công bằng."));
  }, []);

  const ids = me ? [me] : Object.keys(soDu).slice(0, 8);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "1rem" }}>
      <p style={{ fontSize: 12, color: "var(--nq-ink-muted)" }}>Sổ nợ 4 chiều · không bảng xếp hạng tên</p>
      <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Công bằng</h1>
      {error ? <p role="alert">{error}</p> : null}
      {ids.map((id) => (
        <div key={id} style={{ border: "1px solid var(--nq-line)", borderRadius: 8, padding: "0.75rem", marginBottom: 8 }}>
          <strong>{id === me ? "Bạn" : "Nhân viên"}</strong>
          <ul>
            {Object.entries(soDu[id] || {}).map(([a, v]) => (
              <li key={a}>
                {a}: {v.toFixed(1)} (TB nhóm {(means[a] ?? 0).toFixed(1)})
              </li>
            ))}
          </ul>
        </div>
      ))}
      <Link href="/hom-nay">← Hôm nay</Link>
    </main>
  );
}
