"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { formatLuc, ghiNhanLabel, nvLabel, safeText, viError } from "../../lib/present";
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
  const [suaError, setSuaError] = useState<string | null>(null);
  const [tab, setTab] = useState<"treo" | "sua">("treo");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    Promise.all([
      apiGet<{ items: ViecTreo[] }>("/api/v1/viec-treo")
        .then((d) => {
          setTreo(d.items ?? []);
          setError(null);
        })
        .catch((e) => setError(viError(e, { doing: "tải được danh sách việc treo" }))),
      apiGet<{ items: GhiNhan[] }>("/api/v1/ghi-nhan-sua")
        .then((d) => {
          setSua(d.items ?? []);
          setSuaError(null);
        })
        .catch((e) => setSuaError(viError(e, { doing: "tải được sổ lần sửa" }))),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Quản lý ca"
        title="Việc treo"
        meta="Việc kẹt lại từ phiếu ca, kèm sổ những lần quán sửa lịch — để không ai phải nhớ bằng miệng."
      />
      <TabBar>
        <TabButton active={tab === "treo"} onClick={() => setTab("treo")}>
          Việc treo ({treo.length})
        </TabButton>
        <TabButton active={tab === "sua"} onClick={() => setTab("sua")}>
          Lần sửa lịch ({sua.length})
        </TabButton>
      </TabBar>
      {tab === "treo" && (
        <div className="nq-list">
          {error ? <Alert>{error}</Alert> : null}
          {loading ? <Loading skeleton="list">Đang tải việc treo…</Loading> : null}
          {!loading && !error && treo.length === 0 ? (
            <Empty>Không còn việc treo nào. Ca chạy sạch.</Empty>
          ) : null}
          {treo.map((v) => (
            <article key={v.id} className="nq-item nq-item--accent-danger">
              <p className="nq-item-title">{safeText(v.noi_dung, "Việc treo chưa ghi nội dung")}</p>
              <p className="nq-item-sub">
                {nvLabel(v.nhan_vien)} để lại
                {v.created_at ? ` · ${formatLuc(v.created_at)}` : ""}
              </p>
            </article>
          ))}
        </div>
      )}
      {tab === "sua" && (
        <div className="nq-list">
          {suaError ? <Alert>{suaError}</Alert> : null}
          {loading ? <Loading skeleton="list">Đang tải sổ lần sửa…</Loading> : null}
          {!loading && !suaError && sua.length === 0 ? (
            <Empty>Chưa có lần sửa nào. Ghim ca hoặc nhả ca sẽ xuất hiện ở đây.</Empty>
          ) : null}
          {sua.map((g, i) => (
            <article key={safeText(g.id, String(i))} className="nq-item">
              <p className="nq-item-title">{ghiNhanLabel(g.loai)}</p>
              <p className="nq-item-sub">
                {nvLabel(g.ai)}
                {g.luc ? ` · ${formatLuc(g.luc)}` : ""}
              </p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
