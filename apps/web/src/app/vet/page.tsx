"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Empty, Kicker, Loading } from "../../ui/kit";

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
      <Kicker>Append-only</Kicker>
      <h1>Vết hệ thống</h1>
      <p className="nq-muted">Mọi đổi lịch, duyệt, ghi sổ đều ghi lại. Không xóa.</p>
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading /> : null}
      {!loading && items.length === 0 ? (
        <Empty>Chưa có vết. Chuyển trạng thái lịch hoặc duyệt hộp thư sẽ xuất hiện ở đây.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={i} className="nq-item">
            <p style={{ margin: 0, fontWeight: 600 }}>{it.hanh ?? "hành động"}</p>
            <p className="nq-muted" style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.82rem" }}>
              {it.ai} · {it.at}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
