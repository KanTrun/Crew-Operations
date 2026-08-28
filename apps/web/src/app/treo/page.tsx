"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnGhost, btnPrimary, Empty, Kicker, Loading } from "../../ui/kit";

type ViecTreo = {
  id: string;
  phieu_id?: string;
  mau?: string;
  noi_dung: string;
  created_at?: string;
  nhan_vien?: string;
};

type GhiNhan = {
  id?: string;
  loai?: string;
  truoc?: unknown;
  sau?: unknown;
  ai?: string;
  luc?: string;
};

export default function TreoPage() {
  const [token, setToken] = useState("");
  const [treo, setTreo] = useState<ViecTreo[]>([]);
  const [sua, setSua] = useState<GhiNhan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"treo" | "sua">("treo");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    Promise.all([
      apiGet<{ items: ViecTreo[] }>("/api/v1/viec-treo")
        .then((d) => setTreo(d.items ?? []))
        .catch(() => setError("Không tải được việc treo.")),
      apiGet<{ items: GhiNhan[] }>("/api/v1/ghi-nhan-sua")
        .then((d) => setSua(d.items ?? []))
        .catch(() => undefined),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Quản lý ca</Kicker>
      <h1>Việc treo</h1>
      {error ? <Alert>{error}</Alert> : null}
      <p style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button onClick={() => setTab("treo")} style={tab === "treo" ? btnPrimary : btnGhost}>
          Việc treo ({treo.length})
        </button>
        <button onClick={() => setTab("sua")} style={tab === "sua" ? btnPrimary : btnGhost}>
          Ghi nhận sửa ({sua.length})
        </button>
      </p>
      {tab === "treo" && (
        <div className="nq-list">
          {loading ? <Loading /> : null}
          {!loading && treo.length === 0 ? <Empty>Không có việc treo.</Empty> : null}
          {treo.map((v) => (
            <article key={v.id} className="nq-item" style={{ borderLeft: "3px solid var(--nq-danger)" }}>
              <p style={{ margin: 0, fontWeight: 600 }}>{v.noi_dung}</p>
              <p className="nq-muted" style={{ margin: "0.35rem 0 0", fontSize: "0.82rem" }}>
                {v.nhan_vien ? `NV ${v.nhan_vien}` : ""}
                {v.phieu_id ? ` · phiếu ${v.phieu_id}` : ""}
              </p>
            </article>
          ))}
        </div>
      )}
      {tab === "sua" && (
        <div className="nq-list">
          {loading ? <Loading /> : null}
          {!loading && sua.length === 0 ? (
            <Empty>Chưa có lần sửa. Nhả/nhận ca hoặc ghim ô sẽ ghi vào đây.</Empty>
          ) : null}
          {sua.map((g, i) => (
            <article key={g.id ?? String(i)} className="nq-item">
              <p style={{ margin: 0, fontWeight: 600 }}>{g.loai ?? "sửa"}</p>
              <p className="nq-muted" style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.8rem" }}>
                {JSON.stringify(g.truoc)} → {JSON.stringify(g.sau)}
              </p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
