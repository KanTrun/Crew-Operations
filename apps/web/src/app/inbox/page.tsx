"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { agentLabel, inboxLabel, inboxTone, safeText, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  InlineActions,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
} from "../../ui/kit";

type Item = { id: string; tom_tat: string; trang_thai: string; agent: string };

export default function InboxPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Item[] }>("/api/v1/inbox/rang-buoc")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được hộp thư ràng buộc" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function decide(id: string, quyet_dinh: "duyet" | "tu_choi") {
    setBusy(id);
    setError(null);
    setMsg(null);
    try {
      await apiSend(`/api/v1/inbox/rang-buoc/${id}`, { quyet_dinh });
      setMsg(quyet_dinh === "duyet" ? "Đã duyệt mục này." : "Đã từ chối mục này.");
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: quyet_dinh === "duyet" ? "duyệt được mục này" : "từ chối được mục này",
          forbidden: "Chỉ quản lý hoặc chủ quán mới quyết được mục trong hộp thư.",
          missing: "Mục này không còn trong hộp thư — có thể người khác đã quyết. Tải lại hộp thư.",
        }),
      );
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Người duyệt · hệ thống không tự chọn"
        title="Hộp thư ràng buộc"
        meta="Nơi xử những ràng buộc mâu thuẫn nhau: người đọc rồi quyết, hệ thống không chọn hộ."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {!manager ? <Notice>Bạn xem được nội dung. Quản lý hoặc chủ quán mới bấm duyệt.</Notice> : null}
      {loading ? <Loading skeleton="list">Đang mở hộp thư…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Hộp thư sạch — không có ràng buộc nào chờ người quyết.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p className="nq-item-title">{safeText(it.tom_tat, "Ràng buộc chưa có tóm tắt")}</p>
            <p className="nq-item-sub">
              Từ {agentLabel(it.agent)} ·{" "}
              <StatusChip tone={inboxTone(it.trang_thai)}>{inboxLabel(it.trang_thai)}</StatusChip>
            </p>
            {it.trang_thai === "cho_duyet" && manager ? (
              <InlineActions>
                <Btn variant="primary" disabled={busy === it.id} onClick={() => decide(it.id, "duyet")}>
                  Duyệt ràng buộc
                </Btn>
                <Btn variant="danger" disabled={busy === it.id} onClick={() => decide(it.id, "tu_choi")}>
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
