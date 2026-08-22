"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, btnDanger, btnPrimary, Empty, Kicker, Loading } from "../../ui/kit";

type Item = { id: string; tom_tat: string; trang_thai: string; agent: string };

export default function InboxPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Item[] }>("/api/v1/inbox/rang-buoc")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không tải được hộp thư."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function decide(id: string, quyet_dinh: string) {
    try {
      await apiSend(`/api/v1/inbox/rang-buoc/${id}`, { quyet_dinh });
      load();
    } catch {
      setError("Cần quyền quản lý để duyệt.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Người duyệt · hệ thống không tự chọn</Kicker>
      <h1>Hộp thư ràng buộc</h1>
      <p className="nq-muted">Khi hai claim mâu thuẫn, người quyết. Không tự chọn hộ.</p>
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading>Đang mở hộp thư…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Không có mục chờ.</Empty> : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p style={{ margin: 0 }}>
              <strong>{it.agent}</strong> — {it.tom_tat}
            </p>
            <p className="nq-muted" style={{ margin: "0.25rem 0 0.6rem" }}>
              {it.trang_thai === "cho_duyet" ? "Chờ duyệt" : it.trang_thai}
            </p>
            {it.trang_thai === "cho_duyet" && manager ? (
              <p style={{ display: "flex", gap: "0.5rem", margin: 0 }}>
                <button onClick={() => decide(it.id, "duyet")} style={btnPrimary}>
                  Duyệt
                </button>
                <button onClick={() => decide(it.id, "tu_choi")} style={btnDanger}>
                  Từ chối
                </button>
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}
