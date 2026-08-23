"use client";

import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SopPage() {
  const [q, setQ] = useState("nhiệt độ tủ lạnh bao nhiêu là được?");
  const [a, setA] = useState<{ cau_tra_loi: string; trich_dan: string[]; chua_co: boolean } | null>(null);

  async function ask() {
    const r = await fetch(`${API}/api/v1/sop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    setA(await r.json());
  }

  return (
    <main style={{ maxWidth: 560, margin: "0 auto", padding: "1rem" }}>
      <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Hỏi SOP</h1>
      <p style={{ color: "var(--nq-ink-muted)" }}>Chỉ trả lời từ phiếu YAML và luật đã duyệt.</p>
      <textarea
        value={q}
        onChange={(e) => setQ(e.target.value)}
        rows={3}
        style={{ width: "100%", marginBottom: 8 }}
      />
      <button onClick={ask} style={{ minHeight: 44, padding: "0.5rem 1rem" }}>
        Hỏi
      </button>
      {a && (
        <div style={{ marginTop: 16 }}>
          <p>{a.cau_tra_loi}</p>
          <p style={{ fontSize: 13 }}>Trích dẫn: {a.trich_dan.join(", ") || "(không)"}</p>
        </div>
      )}
      <p style={{ marginTop: 24 }}>
        <Link href="/cam-nang">Cẩm nang</Link>
      </p>
    </main>
  );
}
