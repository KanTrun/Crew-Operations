"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ContractsPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = sessionStorage.getItem("nq_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    setName(sessionStorage.getItem("nq_name") ?? "");
    fetch(`${API}/api/v1/contracts`)
      .then(async (r) => {
        if (!r.ok) throw new Error("contracts_failed");
        return r.json();
      })
      .then(setPayload)
      .catch(() => setError("Không tải được contracts từ API."));
  }, [router]);

  const keys = payload
    ? ["NhanVien", "Ca", "LichTuan", "PhieuMau", "RangBuocTrichXuat"].filter((k) => k in payload)
    : [];

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "1.5rem" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "1rem",
          alignItems: "baseline",
          borderBottom: "1px solid var(--nq-line)",
          paddingBottom: "1rem",
          marginBottom: "1.25rem",
        }}
      >
        <div>
          <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, margin: 0 }}>
            Năm hợp đồng
          </h1>
          <p style={{ margin: "0.35rem 0 0", color: "var(--nq-ink-muted)" }}>{name}</p>
        </div>
        <Link href="/" style={{ minHeight: 44, display: "inline-flex", alignItems: "center" }}>
          Về trang chủ
        </Link>
      </header>
      {error ? (
        <p role="alert" style={{ color: "var(--nq-danger)" }}>
          {error}
        </p>
      ) : null}
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {keys.map((k) => (
          <li
            key={k}
            style={{
              borderBottom: "1px solid var(--nq-line)",
              padding: "0.85rem 0",
              fontFamily: "var(--nq-font-mono)",
              fontSize: "0.9rem",
            }}
          >
            <strong style={{ fontFamily: "var(--nq-font-body)" }}>{k}</strong>
            <pre
              style={{
                margin: "0.5rem 0 0",
                whiteSpace: "pre-wrap",
                color: "var(--nq-ink-muted)",
                maxHeight: 180,
                overflow: "auto",
              }}
            >
              {JSON.stringify(payload?.[k], null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </main>
  );
}
