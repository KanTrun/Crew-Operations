"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, isChuQuan, isManager } from "../../lib/session";
import { Alert, AuthGate, Btn, BtnLink, Empty, Loading, Notice, PageHeader, StatusChip } from "../../ui/kit";

type Generation = {
  id: string;
  channel: "gmail" | "facebook";
  created_at: string;
  policy_action: string;
  rule_version: string;
  draft?: { subject?: string; body?: string };
};

type Proposal = {
  id: string;
  channel: string;
  status: string;
  evidence_count: number;
  rule?: { text?: string; priority?: number };
  updated_at: string;
};

type Summary = {
  evaluation_count: number;
  average_score: number;
  passed_count: number;
  feedback_by_type: Record<string, number>;
};

type OperationStatus = {
  flags: Record<string, boolean>;
  retention_days: number;
};

const STATUS_TONE: Record<string, "default" | "warn" | "danger" | "ok"> = {
  active: "ok",
  approved: "ok",
  pending: "warn",
  conflict_pending: "danger",
  rejected: "danger",
  paused: "warn",
  rolled_back: "danger",
};

export default function AiLearningPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [owner, setOwner] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [operations, setOperations] = useState<OperationStatus | null>(null);
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setOwner(isChuQuan());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(async () => {
    if (!getToken()) return;
    setLoading(true);
    try {
      const [nextSummary, nextOperations, nextGenerations, nextProposals] = await Promise.all([
        apiGet<Summary>("/api/v1/ai/evaluations/summary"),
        apiGet<OperationStatus>("/api/v1/ai/operations/status"),
        apiGet<{ items: Generation[] }>("/api/v1/ai/generations?channel=gmail"),
        apiGet<{ items: Proposal[] }>("/api/v1/ai/rules/proposals"),
      ]);
      setSummary(nextSummary);
      setOperations(nextOperations);
      setGenerations(nextGenerations.items ?? []);
      setProposals(nextProposals.items ?? []);
      setError(null);
    } catch (cause) {
      setError(viError(cause, { doing: "đọc vòng học AI" }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) void load();
  }, [token, load]);

  async function act(id: string, path: string, success: string) {
    setBusy(`${id}:${path}`);
    setNotice(null);
    try {
      await apiSend(path);
      setNotice(success);
      await load();
    } catch (cause) {
      setError(viError(cause, { doing: "cập nhật quy tắc AI", forbidden: "Chỉ chủ quán có thể thực hiện thao tác này." }));
    } finally {
      setBusy(null);
    }
  }

  async function runReflection() {
    setBusy("reflection");
    setNotice(null);
    try {
      const result = await apiSend<{ proposal_id?: string | null }>("/api/v1/ai/reflection/gmail/run");
      setNotice(result.proposal_id ? "Đã tạo đề xuất Gmail mới để chủ quán duyệt." : "Đã phân tích phản hồi; chưa đủ bằng chứng lặp lại để tạo quy tắc.");
      await load();
    } catch (cause) {
      setError(viError(cause, { doing: "chạy phản chiếu Gmail" }));
    } finally {
      setBusy(null);
    }
  }

  async function toggleBreaker() {
    setBusy("breaker");
    setNotice(null);
    try {
      await apiSend("/api/v1/ai/operations/circuit-breaker", { channel: "gmail", open: true });
      setNotice("Đã dừng gửi Gmail bằng AI. Các lệnh gửi mới sẽ bị chặn trước transport.");
    } catch (cause) {
      setError(viError(cause, { doing: "dừng kênh Gmail", forbidden: "Chỉ chủ quán có thể dừng kênh." }));
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;
  if (!manager) {
    return <div className="nq-page"><PageHeader kicker="AI vận hành" title="Không đủ quyền truy cập" /><Notice>Trang này dành cho Quản lý và Chủ quán.</Notice></div>;
  }

  const feedbackTotal = Object.values(summary?.feedback_by_type ?? {}).reduce((total, value) => total + value, 0);
  const noLearningData =
    !error &&
    summary !== null &&
    (summary.evaluation_count ?? 0) === 0 &&
    (summary.passed_count ?? 0) === 0 &&
    feedbackTotal === 0 &&
    generations.length === 0 &&
    proposals.length === 0;
  return (
    <div className="nq-page">
      <PageHeader
        kicker="Generation -> Feedback -> Rule"
        title="Học từ phản hồi AI"
        meta="Theo dõi chất lượng vòng học và tạo đề xuất quy tắc từ phản hồi đã kiểm duyệt."
      />
      <Notice>AI học chỉ từ các lần quản lý/chủ quán duyệt hoặc SỬA nội dung AI đề xuất — AI không tự kích hoạt quy tắc nào. Mọi quy tắc phải qua chủ quán duyệt.</Notice>
      {error ? <Alert>{error}</Alert> : null}
      {notice ? <Alert kind="ok">{notice}</Alert> : null}
      {loading ? <Loading skeleton="stats">Đang tải dữ liệu học AI...</Loading> : null}

      {!loading ? (
        <>
          <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Lần đánh giá" value={String(summary?.evaluation_count ?? 0)} />
            <Metric label="Điểm trung bình" value={`${Math.round((summary?.average_score ?? 0) * 100)}%`} />
            <Metric label="Đạt quality gate" value={String(summary?.passed_count ?? 0)} />
            <Metric label="Phản hồi đã ghi" value={String(feedbackTotal)} />
          </section>

          {noLearningData ? (
            <section className="mb-8 border-2 border-[var(--nq-copper)] bg-[var(--nq-surface)] p-5 md:p-6">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-copper)]">Bắt đầu vòng học</p>
              <h2 className="mt-1 text-xl font-black">Chưa có dữ liệu học</h2>
              <p className="mt-3 max-w-3xl text-sm text-[var(--nq-dim)]">
                Vòng học bắt đầu khi quản lý gửi email qua Trợ lý hoặc duyệt tin khách ở Hộp thư Fanpage. Mỗi lần duyệt/sửa, hệ thống ghi lại bản sinh + phản hồi; lặp đủ 3 lần cùng kiểu, chạy Phản chiếu sẽ sinh đề xuất quy tắc.
              </p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <BtnLink href="/copilot">Gửi mail qua Trợ lý (/copilot)</BtnLink>
                <BtnLink href="/page-quan/fb-inbox" variant="ghost">Duyệt tin Fanpage</BtnLink>
              </div>
            </section>
          ) : null}

          <section className="mb-8 border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-5 md:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-copper)]">Gmail reflection</p>
                <h2 className="mt-1 text-xl font-black">Tạo đề xuất từ các lần quản lý sửa email</h2>
                <p className="mt-2 max-w-2xl text-sm text-[var(--nq-dim)]">Chỉ các pattern có bằng chứng lặp lại mới trở thành proposal. Không có quy tắc nào tự được kích hoạt.</p>
              </div>
              <Btn onClick={runReflection} busy={busy === "reflection"}>Chạy phản chiếu</Btn>
            </div>
          </section>

          <section className="mb-8">
            <div className="mb-3 flex items-end justify-between gap-4"><div><p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-copper)]">Quy tắc</p><h2 className="text-2xl font-black">Đề xuất và phiên bản đang dùng</h2></div><span className="font-mono text-sm text-[var(--nq-dim)]">{proposals.length} proposal</span></div>
            {proposals.length === 0 ? <Empty title="Chưa có đề xuất">Chạy phản chiếu khi đã có các chỉnh sửa email lặp lại.</Empty> : (
              <div className="space-y-3">
                {proposals.map((proposal) => (
                  <article key={proposal.id} className="border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="mb-2 flex flex-wrap gap-2"><StatusChip tone={STATUS_TONE[proposal.status] ?? "default"}>{proposal.status.replace(/_/g, " ")}</StatusChip><StatusChip>{proposal.channel}</StatusChip><span className="font-mono text-xs text-[var(--nq-dim)]">{proposal.evidence_count} bằng chứng</span></div><p className="font-semibold">{proposal.rule?.text ?? "Quy tắc không có nội dung"}</p><p className="mt-1 font-mono text-xs text-[var(--nq-dim)]">Ưu tiên {proposal.rule?.priority ?? 0} · cập nhật {new Date(proposal.updated_at).toLocaleString("vi-VN")}</p></div>
                      {owner ? <div className="flex flex-wrap gap-2">
                        {proposal.status === "pending" || proposal.status === "conflict_pending" ? <Btn onClick={() => act(proposal.id, `/api/v1/ai/rules/proposals/${proposal.id}/approve`, "Đã duyệt proposal.")} busy={busy === `${proposal.id}:/api/v1/ai/rules/proposals/${proposal.id}/approve`}>Duyệt</Btn> : null}
                        {proposal.status === "approved" ? <Btn onClick={() => act(proposal.id, `/api/v1/ai/rules/proposals/${proposal.id}/activate`, "Đã kích hoạt quy tắc.")} busy={busy === `${proposal.id}:/api/v1/ai/rules/proposals/${proposal.id}/activate`}>Kích hoạt</Btn> : null}
                        {proposal.status === "active" ? <Btn variant="ghost" onClick={() => act(proposal.id, `/api/v1/ai/rules/${proposal.id}/pause`, "Đã tạm dừng quy tắc.")} busy={busy === `${proposal.id}:/api/v1/ai/rules/${proposal.id}/pause`}>Tạm dừng</Btn> : null}
                      </div> : null}</div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="mb-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <div className="border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-5"><p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-copper)]">Gmail gần đây</p><h2 className="mb-4 text-xl font-black">Generation đã ghi audit</h2>{generations.length === 0 ? <Empty title="Chưa có generation">Email được kiểm duyệt sẽ xuất hiện tại đây.</Empty> : <div className="space-y-3">{generations.slice(0, 8).map((generation) => <article key={generation.id} className="border-l-4 border-[var(--nq-copper)] bg-[var(--nq-surface-hi)] p-3"><p className="font-semibold">{generation.draft?.subject ?? "Không có subject"}</p><p className="mt-1 line-clamp-2 text-sm text-[var(--nq-dim)]">{generation.draft?.body ?? ""}</p><p className="mt-2 font-mono text-xs text-[var(--nq-dim)]">{generation.policy_action} · rules: {generation.rule_version}</p></article>)}</div>}</div>
            <div className="border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-5"><p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-copper)]">Vận hành</p><h2 className="mb-4 text-xl font-black">Guardrail đang bật</h2><div className="space-y-2">{Object.entries(operations?.flags ?? {}).map(([name, enabled]) => <div key={name} className="flex items-center justify-between gap-3 border-b border-[var(--nq-dim)]/50 py-2"><span className="font-mono text-xs break-all">{name.replace("NHIPQUAN_", "")}</span><StatusChip tone={enabled ? "ok" : "default"}>{enabled ? "bật" : "tắt"}</StatusChip></div>)}</div><p className="mt-4 text-sm text-[var(--nq-dim)]">Retention hiện tại: {operations?.retention_days ?? 180} ngày. Chỉ có dry-run, không xóa tự động.</p>{owner ? <Btn variant="danger" onClick={toggleBreaker} busy={busy === "breaker"} className="mt-5">Dừng Gmail AI</Btn> : <p className="mt-5 text-sm text-[var(--nq-dim)]">Chủ quán có thể dừng khẩn cấp kênh Gmail AI.</p>}</div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-5"><p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-dim)]">{label}</p><p className="mt-2 text-4xl font-black text-[var(--nq-copper)]">{value}</p></div>;
}