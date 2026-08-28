"use client";

/**
 * Page quán — kênh khách Facebook.
 * Trống cho đến khi nối Meta (token). Không nhồi thread giả.
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { safeText, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
    Alert,
    AuthGate,
    Btn,
    Empty,
    Field,
    Loading,
    Notice,
    PageHeader,
    Toasts,
    useToasts,
} from "../../ui/kit";

type Status = {
  mode: string;
  connected: boolean;
  has_token: boolean;
  huong_dan: string;
};

type Thread = {
  id: string;
  tom_tat?: string;
  from?: string;
  replies?: Array<{ text: string; by?: string; at?: string }>;
};

type Draft = {
  id: string;
  noi_dung: string;
  trang_thai: string;
};

export default function PageQuanPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [draftText, setDraftText] = useState("");
  const [replyDraft, setReplyDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { toasts, push, dismiss } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    Promise.all([
      apiGet<Status>("/api/v1/page/status"),
      apiGet<{ items: Thread[] }>("/api/v1/page/threads"),
      apiGet<{ items: Draft[] }>("/api/v1/page/drafts"),
    ])
      .then(([st, th, dr]) => {
        setStatus(st);
        setThreads(th.items ?? []);
        setDrafts(dr.items ?? []);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được Page quán" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function reply(id: string) {
    const text = (replyDraft[id] ?? "").trim();
    if (!text) return;
    try {
      await apiSend(`/api/v1/page/threads/${id}/reply`, { text });
      push("Đã gửi trả lời (lưu trong hệ thống — live Graph khi đã nối Meta).");
      setReplyDraft((m) => ({ ...m, [id]: "" }));
      load();
    } catch (e) {
      setError(viError(e, { doing: "gửi được trả lời" }));
    }
  }

  async function createDraft() {
    if (!draftText.trim()) return;
    try {
      await apiSend("/api/v1/page/drafts", { noi_dung: draftText.trim() });
      setDraftText("");
      push("Đã lưu nháp bài.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "lưu được nháp bài", forbidden: "Chỉ quản lý mới soạn bài page." }));
    }
  }

  async function decideDraft(id: string, quyet_dinh: "duyet" | "tu_choi") {
    try {
      await apiSend(`/api/v1/page/drafts/${id}`, { quyet_dinh });
      push(quyet_dinh === "duyet" ? "Đã duyệt nháp." : "Đã từ chối nháp.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "quyết được nháp bài" }));
    }
  }

  async function treo(id: string) {
    try {
      await apiSend("/api/v1/page/treo", { thread_id: id });
      push("Đã tạo việc treo từ thread page.");
    } catch (e) {
      setError(viError(e, { doing: "tạo được việc treo" }));
    }
  }

  if (!token) return <AuthGate />;

  const connected = Boolean(status?.connected);

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Kênh khách · Facebook"
        title="Page quán"
        meta="Tin và bài trên Page thật. Chưa nối Meta thì trang trống — không dữ liệu giả."
      />

      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc trạng thái page…</Loading> : null}

      {!loading && !connected ? (
        <Empty>
          Chưa nối Facebook Page. Tạo Page trên Facebook, lấy token, điền vào{" "}
          <code className="font-mono text-[var(--nq-copper)]">.env</code> theo{" "}
          <span className="font-mono text-sm">docs/runbooks/facebook-page-connect.md</span>
          {status?.huong_dan ? ` — ${status.huong_dan}` : ""}
        </Empty>
      ) : null}

      {!loading && connected ? (
        <Notice>Đã có token Page. Thread sẽ hiện khi webhook/Graph đổ tin thật.</Notice>
      ) : null}

      {!loading && connected && threads.length === 0 ? (
        <Empty>Chưa có hội thoại nào từ Page — chờ khách nhắn hoặc comment thật.</Empty>
      ) : null}

      {!loading &&
        threads.map((th) => (
          <section
            key={th.id}
            className="mb-6 border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-4"
          >
            <p className="font-bold text-[var(--nq-fg)]">{safeText(th.tom_tat, "Hội thoại")}</p>
            <p className="mb-3 font-mono text-sm text-[var(--nq-dim)]">{safeText(th.from, th.id)}</p>
            <ul className="mb-3 space-y-1 text-sm text-[var(--nq-dim)]">
              {(th.replies ?? []).map((r, i) => (
                <li key={`${th.id}-r-${i}`}>→ {safeText(r.text)}</li>
              ))}
            </ul>
            <Field label="Trả lời">
              <input
                className="w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-2 font-mono"
                value={replyDraft[th.id] ?? ""}
                onChange={(e) => setReplyDraft((m) => ({ ...m, [th.id]: e.target.value }))}
              />
            </Field>
            <div className="mt-2 flex flex-wrap gap-2">
              {manager ? (
                <>
                  <Btn variant="primary" onClick={() => reply(th.id)}>
                    Gửi trả lời
                  </Btn>
                  <Btn variant="ghost" onClick={() => treo(th.id)}>
                    Tạo việc treo
                  </Btn>
                </>
              ) : null}
            </div>
          </section>
        ))}

      {manager ? (
        <section className="mt-10 border-2 border-[var(--nq-copper)] p-4">
          <h2 className="mb-4 text-xl font-black uppercase tracking-tighter text-[var(--nq-copper)]">
            Nháp bài page
          </h2>
          <Field label="Nội dung">
            <textarea
              className="min-h-[100px] w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3"
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
            />
          </Field>
          <Btn variant="primary" onClick={createDraft}>
            Lưu nháp
          </Btn>
          <ul className="mt-6 space-y-3">
            {drafts.map((d) => (
              <li key={d.id} className="border-2 border-[var(--nq-dim)] p-3">
                <p className="text-[var(--nq-fg)]">{safeText(d.noi_dung)}</p>
                <p className="font-mono text-xs text-[var(--nq-dim)]">{safeText(d.trang_thai)}</p>
                {d.trang_thai === "nhap" || d.trang_thai === "cho_duyet" ? (
                  <div className="mt-2 flex gap-2">
                    <Btn variant="primary" onClick={() => decideDraft(d.id, "duyet")}>
                      Duyệt
                    </Btn>
                    <Btn variant="danger" onClick={() => decideDraft(d.id, "tu_choi")}>
                      Từ chối
                    </Btn>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
