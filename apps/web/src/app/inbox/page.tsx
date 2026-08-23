"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, InlineActions, Loading, PageHeader, StatusChip } from "../../ui/kit";

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
      <PageHeader
        kicker="Người duyệt · hệ thống không tự chọn"
        title="Hộp thư ràng buộc"
        meta="Khi hai claim mâu thuẫn, người quyết. Không tự chọn hộ."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang mở hộp thư…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Không có mục chờ.</Empty> : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p className="nq-item-title">
              <strong>{it.agent}</strong> — {it.tom_tat}
            </p>
            <p className="nq-item-sub">
              <StatusChip tone={it.trang_thai === "cho_duyet" ? "warn" : "default"}>
                {it.trang_thai === "cho_duyet" ? "Chờ duyệt" : it.trang_thai}
              </StatusChip>
            </p>
            {it.trang_thai === "cho_duyet" && manager ? (
              <InlineActions>
                <Btn variant="primary" onClick={() => decide(it.id, "duyet")}>
                  Duyệt
                </Btn>
                <Btn variant="danger" onClick={() => decide(it.id, "tu_choi")}>
                  Từ chối
                </Btn>
              </InlineActions>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}
