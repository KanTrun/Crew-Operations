"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Ca = {
  id: string;
  ngay: string;
  bat_dau: string;
  ket_thuc: string;
  vi_tri: string;
  khung?: string;
  trang_thai?: "chua_co_nguoi" | "co_nguoi" | "cua_toi" | string;
  co_the_nha?: boolean;
  co_the_nhan?: boolean;
};

type LichData = {
  ca: Ca[];
  tuan_iso?: string;
};

const btnBase: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 44,
  padding: "0.5rem 1rem",
  border: "none",
  borderRadius: 4,
  fontWeight: 600,
  fontSize: "0.875rem",
  cursor: "pointer",
};

export default function ToiPage() {
  const [token, setToken] = useState("");
  const [data, setData] = useState<LichData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const authHeader = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token],
  );

  const loadLich = useCallback(() => {
    if (!token) return;
    fetch(`${API}/api/v1/toi/lich`, { headers: authHeader() })
      .then(async (r) => {
        if (!r.ok) throw new Error("load_lich");
        return r.json() as Promise<LichData | Ca[]>;
      })
      .then((d) => setData(Array.isArray(d) ? { ca: d } : d))
      .catch(() => setError("Không tải được lịch của bạn."));
  }, [authHeader, token]);

  useEffect(() => {
    loadLich();
  }, [loadLich]);

  async function handleNha(caId: string) {
    setBusy(caId);
    setError(null);
    setMsg(null);
    try {
      const r = await fetch(`${API}/api/v1/ca/nha`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ ca_id: caId }),
      });
      if (!r.ok) throw new Error("nha_failed");
      setMsg("Đã nhả ca thành công.");
      loadLich();
    } catch {
      setError("Không nhả được ca.");
    } finally {
      setBusy(null);
    }
  }

  async function handleNhan(caId: string) {
    setBusy(caId);
    setError(null);
    setMsg(null);
    try {
      const r = await fetch(`${API}/api/v1/ca/nhan`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ ca_id: caId }),
      });
      if (!r.ok) throw new Error("nhan_failed");
      setMsg("Đã nhận ca thành công.");
      loadLich();
    } catch {
      setError("Không nhận được ca.");
    } finally {
      setBusy(null);
    }
  }

  const caList = data?.ca ?? [];

  if (!token) {
    return (
      <main style={{ maxWidth: 480, margin: "0 auto", padding: "2rem 1rem" }}>
        <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Lịch của tôi</h1>
        <p>Đăng nhập rồi mở lại trang này.</p>
        <Link href="/">Về trang chủ</Link>
      </main>
    );
  }
  const grouped: Record<string, Ca[]> = {};
  for (const c of caList) {
    (grouped[c.ngay] ??= []).push(c);
  }
  const days = Object.keys(grouped).sort();

  return (
    <main style={{ maxWidth: 480, margin: "0 auto", padding: "1rem", paddingBottom: "5rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid var(--nq-line)", paddingBottom: "0.75rem" }}>
        <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, margin: 0, fontSize: "1.5rem" }}>
          Lịch của tôi
        </h1>
        <Link href="/" style={{ color: "var(--nq-ink-muted)", fontSize: "0.85rem" }}>← Về trang chủ</Link>
      </header>

      {data?.tuan_iso && (
        <p style={{ color: "var(--nq-ink-muted)", fontSize: "0.8rem", marginBottom: "1rem" }}>
          Tuần: <span style={{ fontFamily: "var(--nq-font-mono)" }}>{data.tuan_iso}</span>
        </p>
      )}

      {error && (
        <p role="alert" style={{ color: "var(--nq-danger)", padding: "0.5rem 0.75rem", border: "1px solid var(--nq-danger)", borderRadius: 4, marginBottom: "1rem", fontSize: "0.875rem" }}>
          {error}
        </p>
      )}

      {msg && (
        <p style={{ color: "var(--nq-accent)", padding: "0.5rem 0.75rem", border: "1px solid var(--nq-accent)", borderRadius: 4, marginBottom: "1rem", fontSize: "0.875rem" }}>
          {msg}
        </p>
      )}

      {caList.length === 0 && !error && (
        <p style={{ color: "var(--nq-ink-muted)" }}>Đang tải lịch…</p>
      )}

      {days.map((ngay) => (
        <div key={ngay} style={{ marginBottom: "1.5rem" }}>
          <p style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.8rem", color: "var(--nq-ink-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            {ngay}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {(grouped[ngay] ?? []).map((c) => {
              const isMine = c.trang_thai === "cua_toi";
              return (
                <div
                  key={c.id}
                  style={{
                    background: "var(--nq-bg-elevated)",
                    border: `1px solid ${isMine ? "var(--nq-accent)" : "var(--nq-line)"}`,
                    borderRadius: 8,
                    padding: "0.875rem 1rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: "0.95rem" }}>{c.vi_tri}</p>
                    <p style={{ margin: "0.2rem 0 0", color: "var(--nq-ink-muted)", fontSize: "0.82rem", fontFamily: "var(--nq-font-mono)" }}>
                      {c.bat_dau} – {c.ket_thuc}
                      {c.khung ? ` · ${c.khung}` : ""}
                    </p>
                    {isMine && (
                      <p style={{ margin: "0.2rem 0 0", color: "var(--nq-accent)", fontSize: "0.75rem", fontWeight: 600 }}>Ca của bạn</p>
                    )}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                    {(isMine || c.co_the_nha) && (
                      <button
                        disabled={busy === c.id}
                        onClick={() => handleNha(c.id)}
                        style={{ ...btnBase, background: "var(--nq-danger, #c0392b)", color: "#fff", fontSize: "0.8rem", minWidth: 72 }}
                      >
                        Nhả
                      </button>
                    )}
                    {(!isMine || c.co_the_nhan) && (
                      <button
                        disabled={busy === c.id}
                        onClick={() => handleNhan(c.id)}
                        style={{ ...btnBase, background: "var(--nq-accent)", color: "var(--nq-accent-ink)", fontSize: "0.8rem", minWidth: 72 }}
                      >
                        Nhận
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </main>
  );
}
