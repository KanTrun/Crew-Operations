"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Empty, Loading, PageHeader } from "../../ui/kit";

type Row = { at?: string; ai?: string; hanh?: string };

export default function VetPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Row[] }>("/api/v1/audit")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không đọc được vết. Cần đăng nhập."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Append-only"
        title="Vết hệ thống"
        meta="Mọi đổi lịch, duyệt, ghi sổ đều ghi lại. Không xóa."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc vết…</Loading> : null}
      {!loading && items.length === 0 ? (
        <Empty>Chưa có vết. Chuyển trạng thái lịch hoặc duyệt hộp thư sẽ xuất hiện ở đây.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={i} className="nq-item">
            <p className="nq-item-title">{it.hanh ?? "hành động"}</p>
            <p className="nq-item-sub" style={{ fontFamily: "var(--nq-font-mono)" }}>
              {it.ai} · {it.at}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
