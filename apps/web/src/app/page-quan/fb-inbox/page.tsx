"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../../lib/api";
import { safeText, viError } from "../../../lib/present";
import { getToken, isChuQuan, isManager } from "../../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Confidence,
  Empty,
  Field,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
  Textarea,
  useToasts,
} from "../../../ui/kit";

type FbItem = {
  id: number;
  source: string;
  external_psid: string;
  external_user_name?: string | null;
  message_text: string;
  detected_intent: string;
  confidence: number;
  policy_action: string;
  assigned_role?: string | null;
  proposed_response?: string | null;
  flagged_reasons?: string[];
  status: string;
  created_at: string;
  expires_at?: string | null;
};

type Stats = {
  by_status: Record<string, number>;
  total: number;
  auto_sent: number;
  auto_rate: number;
  escalation_unacked: number;
};

const INTENT_LABEL: Record<string, string> = {
  chao_hoi: "Chào hỏi",
  hoi_gio_dia_chi: "Giờ / Địa chỉ",
  hoi_menu_gia: "Menu / Giá",
  hoi_khuyen_mai: "Khuyến mãi",
  dat_ban: "Đặt bàn",
  khieu_nai_gop_y: "Khiếu nại / Góp ý",
  tu_van_mon: "Tư vấn món",
  yeu_cau_dac_biet: "Yêu cầu đặc biệt",
  blocked_injection: "Blok bảo mật",
  khac: "Khác",
};

const ACTION_LABEL: Record<string, string> = {
  queue_review: "Chờ duyệt",
  priority_review: "Ưu tiên",
  escalate_owner: "Báo chủ quán",
};

function actionTone(a: string): "warn" | "danger" | "default" {
  if (a === "escalate_owner") return "danger";
  if (a === "priority_review") return "warn";
  return "default";
}

function slaLeft(expiresAt?: string | null): { label: string; overdue: boolean } | null {
  if (!expiresAt) return null;
  const end = new Date(`${expiresAt}Z`).getTime();
  if (!Number.isFinite(end)) return null;
  const diff = Math.round((end - Date.now()) / 1000);
  if (diff <= 0) return { label: "QUÁ HẠN", overdue: true };
  const m = Math.floor(diff / 60);
  const s = diff % 60;
  return { label: `${m}:${s.toString().padStart(2, "0")}`, overdue: false };
}

export default function FbInboxPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [chuQuan, setChuQuan] = useState(false);
  const [items, setItems] = useState<FbItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const { push } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: FbItem[] }>("/api/v1/page/fb-inbox?status=pending&limit=100")
      .then((d) => setItems(d.items ?? []))
      .catch((e) => setError(viError(e, { doing: "đọc hộp thư Facebook" })))
      .finally(() => setLoading(false));
    apiGet<Stats>("/api/v1/page/fb-inbox/stats")
      .then((s) => setStats(s))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function decide(item: FbItem, quyet_dinh: string, noi_dung?: string, ly_do?: string) {
    setBusy(item.id);
    setError(null);
    try {
      const res = await apiSend<{ sent: boolean }>(
        `/api/v1/page/fb-inbox/${item.id}/decide`,
        { quyet_dinh, noi_dung, ly_do },
      );
      push(
        res.sent
          ? "Đã gửi phản hồi cho khách."
          : quyet_dinh === "tu_choi"
            ? "Đã từ chối tin này."
            : "Đã ghi nhận quyết định.",
      );
      setEditing(null);
      setDraft("");
      load();
    } catch (e) {
      setError(viError(e, { doing: "xử lý tin nhắn", conflict: "Tin này vừa được người khác duyệt." }));
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;
  if (!manager) {
    return (
      <div className="nq-page">
        <PageHeader kicker="Kiểm duyệt" title="Không có quyền truy cập" />
        <Notice>Bạn cần là Quản lý hoặc Chủ quán để duyệt tin nhắn Fanpage.</Notice>
      </div>
    );
  }

  return (
    <div className="nq-page">
      <PageHeader
        kicker="AG-FBPAGE · Kiểm duyệt chỉn chu"
        title="Hộp thư Fanpage chờ duyệt"
        meta="Tin nhắn khách được policy engine phân loại. Mặc định cần người duyệt — auto-send chỉ cho nhóm thông tin an toàn."
      />

      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang tải hộp thư…</Loading> : null}

      {stats ? (
        <div className="mb-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCell label="Chờ duyệt" value={String(stats.by_status.pending ?? 0)} />
          <StatCell label="Tự động gửi" value={String(stats.auto_sent)} />
          <StatCell label="Báo chủ chưa xác nhận" value={String(stats.escalation_unacked)} danger={stats.escalation_unacked > 0} />
          <StatCell label="Tổng xử lý" value={String(stats.total)} />
        </div>
      ) : null}

      {items.length === 0 && !loading ? (
        <Empty>Không có tin nhắn nào chờ duyệt. Khách nhắn sẽ xuất hiện ở đây.</Empty>
      ) : null}

      <div className="space-y-6">
        {items.map((it) => {
          const ownerOnly = it.assigned_role === "chu_quan" && !chuQuan;
          const sla = slaLeft(it.expires_at);
          const canAct = !ownerOnly;
          return (
            <article
              key={it.id}
              className={`bg-[var(--nq-surface)] border-2 p-6 ${
                sla?.overdue ? "border-[var(--nq-red)]" : "border-[var(--nq-dim)]"
              }`}
            >
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <StatusChip tone={actionTone(it.policy_action)}>
                  {ACTION_LABEL[it.policy_action] ?? safeText(it.policy_action)}
                </StatusChip>
                <StatusChip>{INTENT_LABEL[it.detected_intent] ?? safeText(it.detected_intent)}</StatusChip>
                <Confidence value={it.confidence} />
                {it.source === "comment" ? <StatusChip>Comment</StatusChip> : null}
                {sla ? (
                  <span className={`font-mono text-xs ${sla.overdue ? "text-[var(--nq-red)] font-bold" : "text-[var(--nq-dim)]"}`}>
                    SLA {sla.label}
                  </span>
                ) : null}
                {ownerOnly ? <span className="text-xs text-[var(--nq-red)] uppercase tracking-widest">Chỉ chủ quán duyệt</span> : null}
              </div>

              <p className="text-[var(--nq-fg)] text-lg font-bold mb-2">
                {safeText(it.external_user_name, "Khách hàng")}
              </p>
              <p className="text-[var(--nq-fg)] mb-4 whitespace-pre-wrap break-words">
                {safeText(it.message_text)}
              </p>

              {it.proposed_response ? (
                <div className="mb-4 border-l-4 border-[var(--nq-copper)] pl-4">
                  <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-dim)] mb-1">
                    Bản nháp của agent
                  </p>
                  <p className="text-[var(--nq-dim)] whitespace-pre-wrap break-words">
                    {safeText(it.proposed_response)}
                  </p>
                </div>
              ) : null}

              {Array.isArray(it.flagged_reasons) && it.flagged_reasons.length > 0 ? (
                <Notice>Cờ kiểm duyệt: {it.flagged_reasons.join(", ")}</Notice>
              ) : null}

              {editing === it.id ? (
                <div className="mb-4">
                  <Field label="Sửa nội dung trước khi gửi">
                    <Textarea
                      value={draft}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
                      rows={3}
                    />
                  </Field>
                  <div className="flex gap-3 mt-3">
                    <Btn
                      onClick={() => decide(it, "sua_gui", draft)}
                      busy={busy === it.id}
                      disabled={!draft.trim()}
                    >
                      Gửi bản đã sửa
                    </Btn>
                    <Btn variant="ghost" onClick={() => { setEditing(null); setDraft(""); }}>
                      Hủy
                    </Btn>
                  </div>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <Btn
                  disabled={!canAct}
                  busy={busy === it.id}
                  onClick={() => decide(it, "duyet")}
                  title={it.proposed_response ? "Gửi đúng bản nháp" : "Cần bản nháp để duyệt"}
                >
                  Duyệt &amp; gửi
                </Btn>
                <Btn
                  variant="ghost"
                  disabled={!canAct || !it.proposed_response}
                  onClick={() => { setEditing(it.id); setDraft(it.proposed_response ?? ""); }}
                >
                  Sửa rồi gửi
                </Btn>
                <Btn
                  variant="danger"
                  disabled={!canAct}
                  onClick={() => decide(it, "tu_choi", undefined, "Từ chối khi duyệt")}
                >
                  Từ chối
                </Btn>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function StatCell({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4">
      <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-dim)] mb-1">{label}</p>
      <p className={`text-3xl font-black ${danger ? "text-[var(--nq-red)]" : "text-[var(--nq-fg)]"}`}>{value}</p>
    </div>
  );
}
