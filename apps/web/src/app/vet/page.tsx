"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { actorLabel, formatLuc, hanhViLabel, viError } from "../../lib/present";
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
    setLoading(true);
    apiGet<{ items: Row[] }>("/api/v1/audit")
      .then((d) => {
        setItems(d.items ?? []);
        setError(null);
      })
      .catch((e) =>
        setError(
          viError(e, {
            doing: "đọc được vết hệ thống",
            forbidden: "Chỉ quản lý hoặc chủ quán đọc được vết hệ thống.",
          }),
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Chỉ ghi thêm, không xóa"
        title="Vết hệ thống"
        meta="Mọi lần đổi lịch, duyệt ràng buộc, ghi sổ đều để lại vết ở đây — để tra lại khi cần đối chiếu."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc vết hệ thống…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Chưa có vết nào. Chuyển trạng thái lịch hoặc duyệt hộp thư sẽ sinh vết đầu tiên.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={`${i}-${it.at ?? ""}`} className="nq-item">
            <p className="nq-item-title">{hanhViLabel(it.hanh)}</p>
            <p className="nq-item-sub">
              {actorLabel(it.ai)} · <span style={{ fontFamily: "var(--nq-font-mono)" }}>{formatLuc(it.at)}</span>
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
