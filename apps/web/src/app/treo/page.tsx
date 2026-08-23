"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Empty,
  Loading,
  PageHeader,
  TabBar,
  TabButton,
} from "../../ui/kit";

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
      <PageHeader kicker="Quản lý ca" title="Việc treo" />
      {error ? <Alert>{error}</Alert> : null}
      <TabBar>
        <TabButton active={tab === "treo"} onClick={() => setTab("treo")}>
          Việc treo ({treo.length})
        </TabButton>
        <TabButton active={tab === "sua"} onClick={() => setTab("sua")}>
          Ghi nhận sửa ({sua.length})
        </TabButton>
      </TabBar>
      {tab === "treo" && (
        <div className="nq-list">
          {loading ? <Loading skeleton="list">Đang tải việc treo…</Loading> : null}
          {!loading && treo.length === 0 ? <Empty>Không có việc treo.</Empty> : null}
          {treo.map((v) => (
            <article key={v.id} className="nq-item nq-item--accent-danger">
              <p className="nq-item-title">{v.noi_dung}</p>
              <p className="nq-item-sub">
                {v.nhan_vien ? `NV ${v.nhan_vien}` : ""}
                {v.phieu_id ? ` · phiếu ${v.phieu_id}` : ""}
              </p>
            </article>
          ))}
        </div>
      )}
      {tab === "sua" && (
        <div className="nq-list">
          {loading ? <Loading skeleton="list">Đang tải ghi nhận…</Loading> : null}
          {!loading && sua.length === 0 ? <Empty>Chưa có ghi nhận sửa.</Empty> : null}
          {sua.map((g, i) => (
            <article key={g.id ?? i} className="nq-item">
              <p className="nq-item-title">{g.loai ?? "sửa"}</p>
              <p className="nq-item-sub">
                {g.ai ? `${g.ai} · ` : ""}
                {g.luc ?? ""}
              </p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
