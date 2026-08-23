"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HandoverPage() {
  const [token, setToken] = useState("");
  const [text, setText] = useState(
    "Tình hình: hết đá\nBối cảnh: ca sáng đông\nĐánh giá: máy pha ổn\nĐề nghị: mua đá\nTreo: khăn ướt",
  );
  const [out, setOut] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  async function run() {
    const r = await fetch(`${API}/api/v1/handover`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text, alt_claim: "không hết đá" }),
    });
    setOut(await r.json());
  }

  if (!token) {
    return (
      <main style={{ padding: "2rem" }}>
        <Link href="/">Đăng nhập</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 560, margin: "0 auto", padding: "1rem" }}>
      <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Bàn giao SBAR</h1>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} style={{ width: "100%" }} />
      <p>
        <button onClick={run} style={{ minHeight: 44, marginTop: 8 }}>
          Tách SBAR
        </button>
      </p>
      {out && (
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{JSON.stringify(out, null, 2)}</pre>
      )}
    </main>
  );
}
