"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ViecTreo = {
  id: string;
  phieu_id?: string;
  mau?: string;
  noi_dung: string;
  created_at?: string;
  nhan_vien?: string;
};

type GhiNhanSua = {
  id: string;
  buoc_ma?: string;
  buoc_ten?: string;
  truoc?: string;
  sau?: string;
  created_at?: string;
  phieu_id?: string;
};

export default function TreoPage() {
  const [token, setToken] = useState("");
  const [viecTreo, setViecTreo] = useState<ViecTreo[]>([]);
  const [ghiNhan, setGhiNhan] = useState<GhiNhanSua[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"treo" | "sua">("treo");

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const authHeader = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token],
  );

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/v1/viec-treo`, { headers: authHeader() })
      .then(async (r) => {
        if (!r.ok) throw new Error("load_treo");
        return r.json() as Promise<ViecTreo[] | { items: ViecTreo[] }>;
      })
      .then((d) => setViecTreo(Array.isArray(d) ? d : d.items ?? []))
      .catch(() => setError("Không tải được việc treo."));
  }, [authHeader]);

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/v1/ghi-nhan-sua`, { headers: authHeader() })
      .then(async (r) => {
        if (!r.ok) throw new Error("load_sua");
        return r.json() as Promise<GhiNhanSua[] | { items: GhiNhanSua[] }>;
      })
      .then((d) => setGhiNhan(Array.isArray(d) ? d : d.items ?? []))
      .catch(() => {/* non-critical */});
  }, [authHeader]);

  const tabBtn = (active: boolean): React.CSSProperties => ({
    padding: "0.5rem 1.25rem",
    minHeight: 44,
    background: active ? "var(--nq-accent)" : "var(--nq-surface)",
    color: active ? "var(--nq-accent-ink)" : "var(--nq-ink)",
    border: "1px solid var(--nq-line)",
    borderRadius: 4,
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "0.9rem",
  });

  if (!token) {
    return (
      <main style={{ maxWidth: 480, margin: "0 auto", padding: "2rem 1rem" }}>
        <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400 }}>Việc treo</h1>
        <p>Đăng nhập rồi mở lại trang này.</p>
        <Link href="/">Về trang chủ</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 600, margin: "0 auto", padding: "1rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid var(--nq-line)", paddingBottom: "0.75rem" }}>
        <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, margin: 0, fontSize: "1.5rem" }}>
          Quản lý · Việc treo
        </h1>
        <Link href="/" style={{ color: "var(--nq-ink-muted)", fontSize: "0.85rem" }}>← Về trang chủ</Link>
      </header>

      {error && (
        <p role="alert" style={{ color: "var(--nq-danger)", padding: "0.5rem 0.75rem", border: "1px solid var(--nq-danger)", borderRadius: 4, marginBottom: "1rem", fontSize: "0.875rem" }}>
          {error}
        </p>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
        <button onClick={() => setTab("treo")} style={tabBtn(tab === "treo")}>
          Việc treo ({viecTreo.length})
        </button>
        <button onClick={() => setTab("sua")} style={tabBtn(tab === "sua")}>
          Ghi nhận sửa ({ghiNhan.length})
        </button>
      </div>

      {/* Viec treo tab */}
      {tab === "treo" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {viecTreo.length === 0 && (
            <p style={{ color: "var(--nq-ink-muted)" }}>Không có việc treo nào.</p>
          )}
          {viecTreo.map((v) => (
            <div
              key={v.id}
              style={{
                background: "var(--nq-bg-elevated)",
                border: "1px solid var(--nq-line)",
                borderLeft: "3px solid var(--nq-danger, #c0392b)",
                borderRadius: 8,
                padding: "0.875rem 1rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem", marginBottom: "0.35rem" }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: "0.95rem", flex: 1 }}>
                  {v.noi_dung}
                </p>
                {v.mau && (
                  <span style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.72rem", color: "var(--nq-ink-muted)", background: "var(--nq-surface)", padding: "0.15rem 0.4rem", borderRadius: 3, border: "1px solid var(--nq-line)", whiteSpace: "nowrap" }}>
                    {v.mau}
                  </span>
                )}
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--nq-ink-muted)", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                {v.phieu_id && <span>Phiếu: <code style={{ fontFamily: "var(--nq-font-mono)" }}>{v.phieu_id}</code></span>}
                {v.nhan_vien && <span>NV: {v.nhan_vien}</span>}
                {v.created_at && <span>{new Date(v.created_at).toLocaleString("vi-VN")}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Ghi nhan sua tab */}
      {tab === "sua" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {ghiNhan.length === 0 && (
            <p style={{ color: "var(--nq-ink-muted)" }}>Chưa có ghi nhận sửa nào.</p>
          )}
          {ghiNhan.map((g) => (
            <div
              key={g.id}
              style={{
                background: "var(--nq-bg-elevated)",
                border: "1px solid var(--nq-line)",
                borderLeft: "3px solid var(--nq-accent)",
                borderRadius: 8,
                padding: "0.875rem 1rem",
              }}
            >
              <p style={{ margin: "0 0 0.5rem", fontWeight: 600, fontSize: "0.9rem" }}>
                {g.buoc_ten ?? g.buoc_ma ?? "—"}
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.82rem" }}>
                <div style={{ background: "var(--nq-surface)", border: "1px solid var(--nq-line)", padding: "0.4rem 0.6rem", borderRadius: 4 }}>
                  <p style={{ margin: "0 0 0.2rem", fontSize: "0.7rem", color: "var(--nq-ink-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Trước</p>
                  <p style={{ margin: 0, fontFamily: "var(--nq-font-mono)", wordBreak: "break-all" }}>{g.truoc ?? "—"}</p>
                </div>
                <div style={{ background: "var(--nq-surface)", border: "1px solid var(--nq-line)", padding: "0.4rem 0.6rem", borderRadius: 4 }}>
                  <p style={{ margin: "0 0 0.2rem", fontSize: "0.7rem", color: "var(--nq-ink-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Sau</p>
                  <p style={{ margin: 0, fontFamily: "var(--nq-font-mono)", wordBreak: "break-all" }}>{g.sau ?? "—"}</p>
                </div>
              </div>
              <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--nq-ink-muted)", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                {g.phieu_id && <span>Phiếu: <code style={{ fontFamily: "var(--nq-font-mono)" }}>{g.phieu_id}</code></span>}
                {g.created_at && <span>{new Date(g.created_at).toLocaleString("vi-VN")}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
