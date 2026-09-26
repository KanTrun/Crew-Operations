"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, isChuQuan, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  BtnLink,
  Empty,
  Loading,
  Notice,
  PageHeader,
  Stat,
  StatGrid,
  StatusChip,
} from "../../ui/kit";

type Generation = {
  id: string;
  store_id?: string;
  channel: "gmail" | "facebook";
  conversation_id?: string | null;
  created_at: string;
  policy_action: string;
  rule_version: string;
  draft?: { subject?: string | null; body?: string | null };
  agent_version?: string;
  model?: { provider?: string; model_id?: string; temperature?: number };
};

type Proposal = {
  id: string;
  channel: string;
  status: string;
  evidence_count: number;
  rule?: { text?: string; priority?: number };
  updated_at: string;
  created_at?: string;
  rejection_reason?: string | null;
};

type Summary = {
  evaluation_count: number;
  average_score: number;
  passed_count: number;
  feedback_by_type: Record<string, number>;
};

type OperationStatus = {
  store_id?: string;
  flags: Record<string, boolean>;
  retention_days: number;
  breakers?: { gmail?: boolean; facebook?: boolean };
};

type DryRunResult = {
  dry_run: boolean;
  retention_days: number;
  eligible_counts: Record<string, number>;
};

type ReflectionMetrics = {
  feedback_count: number;
  manager_decision_count: number;
  approval_count: number;
  edit_count: number;
  reject_count: number;
  customer_negative_count?: number;
  edit_rate: number;
};

type ReflectionResult = {
  version: string;
  store_id: string;
  metrics: ReflectionMetrics;
  proposal_saved: boolean;
  proposal_id?: string | null;
};

type ProposalActionResponse = {
  ok?: boolean;
  reason?: string;
  conflicts?: string[];
  proposal?: Proposal;
};

const STATUS_META: Record<string, { label: string; tone: "default" | "warn" | "danger" | "ok" | "info" }> = {
  active: { label: "Đang áp dụng", tone: "ok" },
  approved: { label: "Đã duyệt", tone: "ok" },
  pending: { label: "Chờ duyệt", tone: "warn" },
  conflict_pending: { label: "Xung đột quy tắc", tone: "danger" },
  rejected: { label: "Đã từ chối", tone: "danger" },
  paused: { label: "Tạm dừng", tone: "warn" },
  rolled_back: { label: "Đã quay lui", tone: "danger" },
};

const FEEDBACK_META: Record<string, { label: string; note: string; tone: "ok" | "warn" | "danger" | "default" | "info" }> = {
  manager_approve: { label: "Quản lý duyệt", note: "Giữ nguyên bản sinh AI", tone: "ok" },
  manager_edit: { label: "Quản lý sửa", note: "Nguồn chính để AI rút kinh nghiệm", tone: "warn" },
  manager_reject: { label: "Quản lý từ chối", note: "Nội dung AI không đạt", tone: "danger" },
  customer_positive: { label: "Khách khen ngợi", note: "Hài lòng với phản hồi", tone: "ok" },
  customer_negative: { label: "Khách phản ánh", note: "Chưa hài lòng với phản hồi", tone: "danger" },
  customer_followup: { label: "Khách nhắn tiếp", note: "Hội thoại tiếp diễn bình thường", tone: "info" },
  send_success: { label: "Gửi thành công", note: "Chuyển phát qua kênh suôn sẻ", tone: "default" },
  send_failure: { label: "Gửi thất bại", note: "Lỗi kết nối hoặc transport", tone: "danger" },
  manual_rating: { label: "Chấm điểm tay", note: "Đánh giá nội bộ bổ sung", tone: "info" },
};

const FLAG_META: Record<string, { title: string; desc: string }> = {
  NHIPQUAN_FB_AUTO_SEND: { title: "Tự gửi tin Fanpage", desc: "Tự gửi phản hồi an toàn khi tự tin cao" },
  NHIPQUAN_FB_LEARNING_ENABLED: { title: "Học từ tin nhắn Fanpage", desc: "Thu thập phản hồi để tối ưu kịch bản fanpage" },
  NHIPQUAN_MAIL_QUALITY_GATE: { title: "Cổng kiểm soát chất lượng mail", desc: "Chặn gửi email khi điểm chất lượng dưới ngưỡng" },
  NHIPQUAN_MAIL_AUTO_APPROVE: { title: "Tự duyệt email định kỳ", desc: "Bỏ qua bước duyệt tay với email mẫu chuẩn" },
  NHIPQUAN_MAIL_REFLECTION_ENABLED: { title: "Phản chiếu Gmail định kỳ", desc: "Chạy phân tích sửa đổi email của quản lý" },
  NHIPQUAN_RULE_AUTO_APPLY: { title: "Tự kích hoạt quy tắc", desc: "Tự động kích hoạt (mặc định luôn tắt để người duyệt)" },
  NHIPQUAN_AI_CIRCUIT_BREAKER: { title: "Cầu chì an toàn AI toàn cục", desc: "Ngắt khẩn cấp mọi hoạt động gửi tự động" },
  NHIPQUAN_AI_CANARY_ENABLED: { title: "Thử nghiệm Canary", desc: "Áp dụng tập quy tắc mới cho tỷ lệ nhỏ" },
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

  // Filter & interaction states
  const [proposalChannelFilter, setProposalChannelFilter] = useState<"all" | "gmail" | "facebook">("all");
  const [proposalStatusFilter, setProposalStatusFilter] = useState<string>("all");
  const [genChannelFilter, setGenChannelFilter] = useState<"all" | "gmail" | "facebook">("all");
  const [expandedGenerations, setExpandedGenerations] = useState<Record<string, boolean>>({});
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [lastReflection, setLastReflection] = useState<{
    channel: "gmail" | "facebook";
    metrics: ReflectionMetrics;
    proposal_id?: string | null;
  } | null>(null);
  const [breakers, setBreakers] = useState<{ gmail: boolean; facebook: boolean }>({
    gmail: false,
    facebook: false,
  });

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
        apiGet<{ items: Generation[] }>("/api/v1/ai/generations"),
        apiGet<{ items: Proposal[] }>("/api/v1/ai/rules/proposals"),
      ]);
      setSummary(nextSummary);
      setOperations(nextOperations);
      setGenerations(nextGenerations.items ?? []);
      setProposals(nextProposals.items ?? []);
      if (nextOperations?.breakers) {
        setBreakers({
          gmail: Boolean(nextOperations.breakers.gmail),
          facebook: Boolean(nextOperations.breakers.facebook),
        });
      }
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

  async function approveProposal(proposal: Proposal) {
    setBusy(`approve:${proposal.id}`);
    setError(null);
    setNotice(null);
    try {
      const res = await apiSend<ProposalActionResponse>(
        `/api/v1/ai/rules/proposals/${proposal.id}/approve`
      );
      if (res.ok === false && res.reason === "rule_conflict") {
        setError(
          `Xung đột quy tắc: Quy tắc này mâu thuẫn với quy tắc đã có (${(res.conflicts ?? []).join(
            ", "
          )}). Hệ thống đã chuyển sang trạng thái xung đột để kiểm tra.`
        );
      } else {
        setNotice("Đã duyệt quy tắc. Chủ quán có thể bấm Kích hoạt để áp dụng ngay vào vận hành.");
      }
      await load();
    } catch (cause) {
      setError(
        viError(cause, {
          doing: "duyệt đề xuất quy tắc",
          forbidden: "Chỉ chủ quán mới có quyền duyệt quy tắc AI.",
        })
      );
    } finally {
      setBusy(null);
    }
  }

  async function activateProposal(proposal: Proposal) {
    setBusy(`activate:${proposal.id}`);
    setError(null);
    setNotice(null);
    try {
      await apiSend(`/api/v1/ai/rules/proposals/${proposal.id}/activate`);
      setNotice("Đã kích hoạt quy tắc! AI sẽ bắt đầu áp dụng quy tắc này trong các lượt sinh tiếp theo.");
      await load();
    } catch (cause) {
      setError(
        viError(cause, {
          doing: "kích hoạt quy tắc",
          forbidden: "Chỉ chủ quán mới có quyền kích hoạt quy tắc.",
        })
      );
    } finally {
      setBusy(null);
    }
  }

  async function pauseProposal(proposal: Proposal) {
    setBusy(`pause:${proposal.id}`);
    setError(null);
    setNotice(null);
    try {
      await apiSend(`/api/v1/ai/rules/${proposal.id}/pause`);
      setNotice("Đã tạm dừng quy tắc. AI sẽ tạm thời không áp dụng quy tắc này.");
      await load();
    } catch (cause) {
      setError(
        viError(cause, {
          doing: "tạm dừng quy tắc",
          forbidden: "Chỉ chủ quán mới có quyền tạm dừng quy tắc.",
        })
      );
    } finally {
      setBusy(null);
    }
  }

  async function rollbackProposal(proposal: Proposal) {
    setBusy(`rollback:${proposal.id}`);
    setError(null);
    setNotice(null);
    try {
      await apiSend(`/api/v1/ai/rules/${proposal.id}/rollback`);
      setNotice("Đã quay lui quy tắc.");
      await load();
    } catch (cause) {
      setError(
        viError(cause, {
          doing: "quay lui quy tắc",
          forbidden: "Chỉ chủ quán mới có quyền quay lui quy tắc.",
        })
      );
    } finally {
      setBusy(null);
    }
  }

  async function confirmReject(proposalId: string) {
    setBusy(`reject:${proposalId}`);
    setError(null);
    setNotice(null);
    try {
      await apiSend(`/api/v1/ai/rules/proposals/${proposalId}/reject`, {
        reason: rejectionReason.trim() || undefined,
      });
      setNotice("Đã từ chối đề xuất quy tắc.");
      setRejectingId(null);
      setRejectionReason("");
      await load();
    } catch (cause) {
      setError(
        viError(cause, {
          doing: "từ chối quy tắc",
          forbidden: "Chỉ chủ quán mới có quyền từ chối quy tắc.",
        })
      );
    } finally {
      setBusy(null);
    }
  }

  async function runReflection(channel: "gmail" | "facebook") {
    setBusy(`reflection:${channel}`);
    setError(null);
    setNotice(null);
    try {
      const result = await apiSend<ReflectionResult>(
        `/api/v1/ai/reflection/${channel}/run`
      );
      setLastReflection({
        channel,
        metrics: result.metrics,
        proposal_id: result.proposal_id,
      });
      const channelUpper = channel === "gmail" ? "Gmail" : "Facebook";
      if (result.proposal_id) {
        setNotice(
          `Đã phân tích xong ${channelUpper}! Tạo thành công đề xuất quy tắc mới (ID: ${result.proposal_id}). Chủ quán vui lòng duyệt bên dưới.`
        );
      } else {
        const edits = result.metrics?.edit_count ?? 0;
        const total = result.metrics?.feedback_count ?? 0;
        setNotice(
          `Đã phân tích xong ${channelUpper} (${total} phản hồi, ${edits} lần sửa). Hiện tại chưa đủ mẫu sửa đổi lặp lại (cần tối thiểu 3 lần cùng kiểu) để đề xuất quy tắc mới.`
        );
      }
      await load();
    } catch (cause) {
      setError(viError(cause, { doing: `chạy phản chiếu ${channel}` }));
    } finally {
      setBusy(null);
    }
  }

  async function toggleBreaker(channel: "gmail" | "facebook") {
    const nextOpen = !breakers[channel];
    setBusy(`breaker:${channel}`);
    setError(null);
    setNotice(null);
    try {
      await apiSend("/api/v1/ai/operations/circuit-breaker", {
        channel,
        open: nextOpen,
      });
      setBreakers((prev) => ({ ...prev, [channel]: nextOpen }));
      const channelLabel = channel === "gmail" ? "Gmail" : "Facebook";
      if (nextOpen) {
        setNotice(`Đã ngắt khẩn cấp kênh ${channelLabel} AI. Mọi lệnh gửi tự động sẽ bị chặn.`);
      } else {
        setNotice(`Đã khôi phục hoạt động bình thường cho kênh ${channelLabel} AI.`);
      }
      await load();
    } catch (cause) {
      setError(
        viError(cause, {
          doing: `đổi trạng thái cầu chì kênh ${channel}`,
          forbidden: "Chỉ chủ quán có quyền can thiệp cầu chì an toàn.",
        })
      );
    } finally {
      setBusy(null);
    }
  }

  async function runDryRun() {
    setDryRunLoading(true);
    setError(null);
    try {
      const res = await apiGet<DryRunResult>("/api/v1/ai/retention/dry-run");
      setDryRunResult(res);
    } catch (cause) {
      setError(
        viError(cause, {
          doing: "kiểm tra dọn dẹp dữ liệu",
          forbidden: "Chỉ chủ quán có quyền chạy kiểm tra dọn dẹp.",
        })
      );
    } finally {
      setDryRunLoading(false);
    }
  }

  function toggleExpandGeneration(id: string) {
    setExpandedGenerations((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  if (!token) return <AuthGate />;
  if (!manager) {
    return (
      <div className="nq-page">
        <PageHeader kicker="AI vận hành" title="Không đủ quyền truy cập" />
        <Notice>Trang này chỉ dành cho Quản lý và Chủ quán.</Notice>
      </div>
    );
  }

  const feedbackTotal = Object.values(summary?.feedback_by_type ?? {}).reduce(
    (total, value) => total + value,
    0
  );

  const filteredProposals = proposals.filter((p) => {
    if (proposalChannelFilter !== "all" && p.channel !== proposalChannelFilter) return false;
    if (proposalStatusFilter === "pending") return p.status === "pending" || p.status === "conflict_pending";
    if (proposalStatusFilter !== "all" && p.status !== proposalStatusFilter) return false;
    return true;
  });

  const filteredGenerations = generations.filter((g) => {
    if (genChannelFilter !== "all" && g.channel !== genChannelFilter) return false;
    return true;
  });

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
        kicker="Generation → Feedback → Rule"
        title="Vòng học từ phản hồi AI"
        meta="Theo dõi chất lượng vòng học, phân tích phản hồi quản lý & khách, tạo và kiểm duyệt quy tắc an toàn."
      />

      <Notice>
        AI học có kiểm duyệt (Human-in-the-loop): AI chỉ học từ các lần Quản lý/Chủ quán duyệt hoặc SỬA nội dung AI đề xuất — không có quy tắc nào tự ý kích hoạt ngầm. Mọi quy tắc mới bắt buộc phải qua Chủ quán kiểm duyệt và kích hoạt có chủ đích.
      </Notice>

      {error ? <Alert kind="err" className="mb-6">{error}</Alert> : null}
      {notice ? <Alert kind="ok" className="mb-6">{notice}</Alert> : null}
      {loading ? <Loading skeleton="stats">Đang tải dữ liệu học AI...</Loading> : null}

      {!loading ? (
        <>
          {/* 1. Chỉ số tóm tắt */}
          <StatGrid>
            <Stat
              label="Lần đánh giá chất lượng"
              value={String(summary?.evaluation_count ?? 0)}
              tone="default"
            />
            <Stat
              label="Điểm chất lượng TB"
              value={`${Math.round((summary?.average_score ?? 0) * 100)}%`}
              tone={(summary?.average_score ?? 0) >= 0.7 ? "ok" : "warn"}
            />
            <Stat
              label="Đạt Quality Gate"
              value={`${summary?.passed_count ?? 0} / ${summary?.evaluation_count ?? 0}`}
              tone={(summary?.passed_count ?? 0) > 0 ? "ok" : "default"}
            />
            <Stat
              label="Tổng phản hồi đã ghi"
              value={String(feedbackTotal)}
              tone={feedbackTotal > 0 ? "default" : "warn"}
            />
          </StatGrid>

          {/* Chưa có dữ liệu */}
          {noLearningData ? (
            <section className="mb-8 nq-surface-block border-[var(--nq-accent)] p-5 md:p-6">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">Bắt đầu vòng học</p>
              <h2 className="mt-1 text-xl font-semibold">Chưa có dữ liệu học</h2>
              <p className="mt-3 max-w-3xl text-sm text-[var(--nq-dim)]">
                Vòng học bắt đầu khi quản lý gửi email qua Trợ lý hoặc duyệt tin khách ở Hộp thư Fanpage. Mỗi lần duyệt/sửa, hệ thống ghi lại bản sinh + phản hồi; lặp đủ 3 lần cùng kiểu, chạy Phản chiếu sẽ sinh đề xuất quy tắc.
              </p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <BtnLink href="/copilot">Gửi mail qua Trợ lý (/copilot)</BtnLink>
                <BtnLink href="/page-quan/fb-inbox" variant="ghost">Duyệt tin Fanpage</BtnLink>
              </div>
            </section>
          ) : null}

          {/* 2. Chi tiết phân loại phản hồi (Feedback Breakdown) */}
          <section className="mb-8 nq-surface-block p-5 md:p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--nq-line)] pb-3">
              <div>
                <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                  Cơ sở dữ liệu học tập
                </p>
                <h2 className="text-xl font-semibold">Phân loại phản hồi đã ghi nhận</h2>
              </div>
              <span className="font-mono text-xs text-[var(--nq-dim)]">
                {feedbackTotal} phản hồi qua các kênh
              </span>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Object.entries(summary?.feedback_by_type ?? {}).map(([key, count]) => {
                const meta = FEEDBACK_META[key] ?? {
                  label: key.replace(/_/g, " "),
                  note: "Phản hồi hệ thống",
                  tone: "default" as const,
                };
                return (
                  <div key={key} className="nq-surface-tile flex flex-col justify-between p-3.5">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold">{meta.label}</span>
                        <StatusChip tone={meta.tone}>{count}</StatusChip>
                      </div>
                      <p className="mt-1.5 text-xs text-[var(--nq-dim)]">{meta.note}</p>
                    </div>
                  </div>
                );
              })}
              {Object.keys(summary?.feedback_by_type ?? {}).length === 0 ? (
                <p className="col-span-full text-sm text-[var(--nq-dim)] italic">
                  Chưa ghi nhận phản hồi nào. Hãy thử gửi mail hoặc duyệt tin nhắn Fanpage.
                </p>
              ) : null}
            </div>
          </section>

          {/* 3. Phản chiếu & Sinh quy tắc (Reflection Engine) */}
          <section className="mb-8 nq-surface-block p-5 md:p-6">
            <div className="border-b border-[var(--nq-line)] pb-3">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                Reflection Engine
              </p>
              <h2 className="text-xl font-semibold">Chạy phản chiếu & Rút trích quy tắc mới</h2>
              <p className="mt-1 text-sm text-[var(--nq-dim)]">
                Phân tích các lần Quản lý sửa đổi nội dung hoặc phản hồi khách hàng. Khi phát hiện quy luật lặp lại tối thiểu 3 lần, hệ thống sẽ đề xuất quy tắc mới để Chủ quán duyệt.
              </p>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {/* Gmail Reflection */}
              <div className="nq-surface-tile flex flex-col justify-between p-5">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                      Kênh Gmail
                    </span>
                    <StatusChip tone="info">Email nội bộ & đối tác</StatusChip>
                  </div>
                  <h3 className="mt-2 text-lg font-semibold">Phản chiếu Gmail</h3>
                  <p className="mt-1 text-sm text-[var(--nq-dim)]">
                    Phân tích các lần quản lý sửa mail nhắc ca, thông báo lịch, hoặc soạn thảo tự động.
                  </p>
                </div>
                <div className="mt-4 pt-4 border-t border-[var(--nq-line)]">
                  <Btn
                    onClick={() => runReflection("gmail")}
                    busy={busy === "reflection:gmail"}
                    className="w-full sm:w-auto"
                  >
                    Chạy phản chiếu Gmail
                  </Btn>
                </div>
              </div>

              {/* Facebook Reflection */}
              <div className="nq-surface-tile flex flex-col justify-between p-5">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                      Kênh Fanpage Facebook
                    </span>
                    <StatusChip tone="info">Tin nhắn khách hàng</StatusChip>
                  </div>
                  <h3 className="mt-2 text-lg font-semibold">Phản chiếu Facebook</h3>
                  <p className="mt-1 text-sm text-[var(--nq-dim)]">
                    Phân tích các lần quản lý sửa tin tư vấn, đặt bàn, hoặc phản hồi khách hàng ở Hộp thư Fanpage.
                  </p>
                </div>
                <div className="mt-4 pt-4 border-t border-[var(--nq-line)]">
                  <Btn
                    onClick={() => runReflection("facebook")}
                    busy={busy === "reflection:facebook"}
                    className="w-full sm:w-auto"
                  >
                    Chạy phản chiếu Facebook
                  </Btn>
                </div>
              </div>
            </div>

            {/* Báo cáo lượt phản chiếu vừa chạy */}
            {lastReflection ? (
              <div className="mt-5 rounded-lg border border-[var(--nq-line)] bg-[var(--nq-surface-hi)] p-4">
                <p className="text-xs font-mono uppercase tracking-wider text-[var(--nq-accent)]">
                  Kết quả phân tích vừa chạy ({lastReflection.channel.toUpperCase()})
                </p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                  <div>
                    <span className="text-xs text-[var(--nq-dim)] block">Phản hồi quét:</span>
                    <span className="font-semibold">{lastReflection.metrics.feedback_count}</span>
                  </div>
                  <div>
                    <span className="text-xs text-[var(--nq-dim)] block">Quyết định quản lý:</span>
                    <span className="font-semibold">{lastReflection.metrics.manager_decision_count}</span>
                  </div>
                  <div>
                    <span className="text-xs text-[var(--nq-dim)] block">Lần quản lý sửa:</span>
                    <span className="font-semibold">{lastReflection.metrics.edit_count}</span>
                  </div>
                  <div>
                    <span className="text-xs text-[var(--nq-dim)] block">Tỷ lệ sửa:</span>
                    <span className="font-semibold">{Math.round(lastReflection.metrics.edit_rate * 100)}%</span>
                  </div>
                </div>
              </div>
            ) : null}
          </section>

          {/* 4. Quy tắc & Đề xuất (Rules & Proposals) */}
          <section className="mb-8 nq-surface-block p-5 md:p-6">
            <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--nq-line)] pb-4">
              <div>
                <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                  Human-in-the-loop Governance
                </p>
                <h2 className="text-xl font-semibold">Quy tắc AI & Đề xuất kiểm duyệt</h2>
                <p className="mt-1 text-sm text-[var(--nq-dim)]">
                  Chủ quán có toàn quyền kiểm duyệt, kích hoạt, tạm dừng hoặc quay lui mọi quy tắc.
                </p>
              </div>
              <span className="font-mono text-sm text-[var(--nq-dim)]">
                {filteredProposals.length} / {proposals.length} quy tắc
              </span>
            </div>

            {/* Filter Tabs */}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--nq-line)] pb-3">
              <div className="flex flex-wrap gap-1.5 text-xs">
                <span className="self-center mr-1 text-[var(--nq-dim)] font-mono">Kênh:</span>
                {(["all", "gmail", "facebook"] as const).map((ch) => (
                  <button
                    key={ch}
                    type="button"
                    onClick={() => setProposalChannelFilter(ch)}
                    className={`rounded px-2.5 py-1 font-mono transition-colors ${
                      proposalChannelFilter === ch
                        ? "bg-[var(--nq-accent)] text-black font-semibold"
                        : "bg-[var(--nq-surface-hi)] text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"
                    }`}
                  >
                    {ch === "all" ? "Tất cả kênh" : ch.toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap gap-1.5 text-xs">
                <span className="self-center mr-1 text-[var(--nq-dim)] font-mono">Trạng thái:</span>
                {[
                  { id: "all", label: "Tất cả" },
                  { id: "pending", label: "Chờ duyệt" },
                  { id: "active", label: "Đang áp dụng" },
                  { id: "approved", label: "Đã duyệt" },
                  { id: "paused", label: "Tạm dừng" },
                  { id: "rejected", label: "Đã từ chối" },
                ].map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => setProposalStatusFilter(st.id)}
                    className={`rounded px-2.5 py-1 font-mono transition-colors ${
                      proposalStatusFilter === st.id
                        ? "bg-[var(--nq-accent)] text-black font-semibold"
                        : "bg-[var(--nq-surface-hi)] text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"
                    }`}
                  >
                    {st.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Danh sách proposals */}
            {filteredProposals.length === 0 ? (
              <div className="py-8">
                <Empty title="Chưa có đề xuất quy tắc">
                  {proposals.length === 0
                    ? "Chạy phản chiếu sau khi quản lý đã thực hiện sửa đổi email hoặc tin nhắn để phát hiện pattern lặp lại."
                    : "Không có quy tắc nào khớp với bộ lọc hiện tại."}
                </Empty>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {filteredProposals.map((proposal) => {
                  const meta = STATUS_META[proposal.status] ?? {
                    label: proposal.status.replace(/_/g, " "),
                    tone: "default" as const,
                  };
                  const isRejecting = rejectingId === proposal.id;

                  return (
                    <article
                      key={proposal.id}
                      className="nq-surface-tile p-4 sm:p-5 transition-colors"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="max-w-3xl space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusChip tone={meta.tone}>{meta.label}</StatusChip>
                            <StatusChip tone="info">{proposal.channel.toUpperCase()}</StatusChip>
                            <span className="font-mono text-xs text-[var(--nq-dim)]">
                              {proposal.evidence_count} bằng chứng
                            </span>
                            <span className="font-mono text-xs text-[var(--nq-dim)]">
                              · Ưu tiên: {proposal.rule?.priority ?? 0}
                            </span>
                          </div>

                          <p className="text-base font-semibold leading-relaxed">
                            {proposal.rule?.text ?? "Quy tắc không có nội dung"}
                          </p>

                          {proposal.rejection_reason ? (
                            <p className="text-xs text-[var(--nq-red)] italic">
                              Lý do từ chối: {proposal.rejection_reason}
                            </p>
                          ) : null}

                          {proposal.status === "conflict_pending" ? (
                            <p className="text-xs text-[var(--nq-warn)]">
                              ⚠️ Phát hiện xung đột với một quy tắc khác đang hoạt động. Cần xem xét trước khi áp dụng.
                            </p>
                          ) : null}

                          <p className="font-mono text-xs text-[var(--nq-dim)]">
                            Cập nhật: {new Date(proposal.updated_at).toLocaleString("vi-VN")}
                          </p>
                        </div>

                        {/* Thao tác của Chủ quán */}
                        {owner ? (
                          <div className="flex flex-wrap items-center gap-2">
                            {/* Chờ duyệt */}
                            {proposal.status === "pending" || proposal.status === "conflict_pending" ? (
                              <>
                                <Btn
                                  onClick={() => approveProposal(proposal)}
                                  busy={busy === `approve:${proposal.id}`}
                                >
                                  Duyệt
                                </Btn>
                                {!isRejecting ? (
                                  <Btn
                                    variant="ghost"
                                    onClick={() => {
                                      setRejectingId(proposal.id);
                                      setRejectionReason("");
                                    }}
                                  >
                                    Từ chối
                                  </Btn>
                                ) : null}
                              </>
                            ) : null}

                            {/* Đã duyệt */}
                            {proposal.status === "approved" ? (
                              <>
                                <Btn
                                  onClick={() => activateProposal(proposal)}
                                  busy={busy === `activate:${proposal.id}`}
                                >
                                  Kích hoạt
                                </Btn>
                                {!isRejecting ? (
                                  <Btn
                                    variant="ghost"
                                    onClick={() => {
                                      setRejectingId(proposal.id);
                                      setRejectionReason("");
                                    }}
                                  >
                                    Huỷ / Từ chối
                                  </Btn>
                                ) : null}
                              </>
                            ) : null}

                            {/* Đang áp dụng */}
                            {proposal.status === "active" ? (
                              <>
                                <Btn
                                  variant="ghost"
                                  onClick={() => pauseProposal(proposal)}
                                  busy={busy === `pause:${proposal.id}`}
                                >
                                  Tạm dừng
                                </Btn>
                                <Btn
                                  variant="danger"
                                  onClick={() => rollbackProposal(proposal)}
                                  busy={busy === `rollback:${proposal.id}`}
                                >
                                  Quay lui
                                </Btn>
                              </>
                            ) : null}

                            {/* Tạm dừng */}
                            {proposal.status === "paused" ? (
                              <>
                                <Btn
                                  onClick={() => activateProposal(proposal)}
                                  busy={busy === `activate:${proposal.id}`}
                                >
                                  Kích hoạt lại
                                </Btn>
                                <Btn
                                  variant="danger"
                                  onClick={() => rollbackProposal(proposal)}
                                  busy={busy === `rollback:${proposal.id}`}
                                >
                                  Quay lui
                                </Btn>
                              </>
                            ) : null}
                          </div>
                        ) : null}
                      </div>

                      {/* Hộp thoại từ chối nhanh */}
                      {isRejecting ? (
                        <div className="mt-4 rounded border border-[var(--nq-line)] bg-[var(--nq-surface-hi)] p-3">
                          <label className="block text-xs font-semibold text-[var(--nq-fg)] mb-1">
                            Lý do từ chối (tuỳ chọn):
                          </label>
                          <input
                            type="text"
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                            placeholder="Nhập lý do không áp dụng quy tắc này..."
                            className="w-full rounded border border-[var(--nq-line)] bg-[var(--nq-bg)] px-3 py-1.5 text-sm font-sans text-[var(--nq-fg)] focus:outline-none focus:border-[var(--nq-accent)]"
                          />
                          <div className="mt-2.5 flex justify-end gap-2">
                            <Btn
                              variant="ghost"
                              onClick={() => {
                                setRejectingId(null);
                                setRejectionReason("");
                              }}
                            >
                              Huỷ
                            </Btn>
                            <Btn
                              variant="danger"
                              onClick={() => confirmReject(proposal.id)}
                              busy={busy === `reject:${proposal.id}`}
                            >
                              Xác nhận từ chối
                            </Btn>
                          </div>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          {/* 5. Hai cột: Generations Audit & Operations Safety */}
          <section className="mb-8 grid gap-6 lg:grid-cols-2">
            {/* Cột 1: Bản sinh gần đây */}
            <div className="nq-surface-block p-5 md:p-6 flex flex-col justify-between">
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--nq-line)] pb-3">
                  <div>
                    <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                      Lịch sử tạo nội dung
                    </p>
                    <h2 className="text-xl font-semibold">Audit bản sinh gần đây</h2>
                  </div>
                  <div className="flex gap-1 text-xs">
                    {(["all", "gmail", "facebook"] as const).map((ch) => (
                      <button
                        key={ch}
                        type="button"
                        onClick={() => setGenChannelFilter(ch)}
                        className={`rounded px-2 py-0.5 font-mono ${
                          genChannelFilter === ch
                            ? "bg-[var(--nq-accent)] text-black font-semibold"
                            : "bg-[var(--nq-surface-hi)] text-[var(--nq-dim)]"
                        }`}
                      >
                        {ch === "all" ? "Tất cả" : ch.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredGenerations.length === 0 ? (
                  <div className="py-8">
                    <Empty title="Chưa có bản sinh">
                      Nội dung email hoặc tin nhắn sinh bởi AI sẽ xuất hiện tại đây sau khi kích hoạt.
                    </Empty>
                  </div>
                ) : (
                  <div className="mt-4 space-y-3">
                    {filteredGenerations.slice(0, 10).map((generation) => {
                      const expanded = Boolean(expandedGenerations[generation.id]);
                      const isFb = generation.channel === "facebook";
                      const title = generation.draft?.subject || (isFb ? "Tin nhắn Fanpage" : "Email gửi đi");
                      const body = generation.draft?.body ?? "";

                      return (
                        <article
                          key={generation.id}
                          className="rounded border-l-4 border-[var(--nq-accent)] bg-[var(--nq-surface-hi)] p-3.5 transition-colors"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-sm truncate">{title}</span>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <StatusChip tone={isFb ? "info" : "warn"}>
                                {generation.channel.toUpperCase()}
                              </StatusChip>
                              <StatusChip
                                tone={generation.policy_action === "auto_send" ? "ok" : "default"}
                              >
                                {generation.policy_action === "auto_send" ? "Tự gửi" : "Chờ duyệt"}
                              </StatusChip>
                            </div>
                          </div>

                          <p
                            className={`mt-2 text-sm text-[var(--nq-dim)] whitespace-pre-wrap ${
                              !expanded ? "line-clamp-2" : ""
                            }`}
                          >
                            {body || "(Không có nội dung)"}
                          </p>

                          {body && body.length > 120 ? (
                            <button
                              type="button"
                              onClick={() => toggleExpandGeneration(generation.id)}
                              className="mt-1 text-xs text-[var(--nq-accent)] underline hover:no-underline font-mono"
                            >
                              {expanded ? "Thu gọn" : "Xem toàn bộ nội dung"}
                            </button>
                          ) : null}

                          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-2xs text-[var(--nq-dim)] border-t border-[var(--nq-line)] pt-2">
                            <span>Quy tắc: {generation.rule_version}</span>
                            <span>Agent: {generation.agent_version || "n/a"}</span>
                            <span>{new Date(generation.created_at).toLocaleString("vi-VN")}</span>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>

              {filteredGenerations.length > 10 ? (
                <p className="mt-4 text-center font-mono text-xs text-[var(--nq-dim)]">
                  Đang hiển thị 10 / {filteredGenerations.length} bản sinh mới nhất.
                </p>
              ) : null}
            </div>

            {/* Cột 2: Vận hành & Cầu chì an toàn */}
            <div className="nq-surface-block p-5 md:p-6 flex flex-col justify-between">
              <div>
                <div className="border-b border-[var(--nq-line)] pb-3">
                  <p className="font-mono text-xs uppercase tracking-widest text-[var(--nq-accent)]">
                    An toàn hệ thống
                  </p>
                  <h2 className="text-xl font-semibold">Guardrail & Cầu chì ngắt khẩn cấp</h2>
                  <p className="mt-1 text-sm text-[var(--nq-dim)]">
                    Kiểm soát hành vi tự động và ngắt ngay lập tức khi phát hiện sự cố bất thường.
                  </p>
                </div>

                {/* Circuit Breakers */}
                <div className="mt-4 space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--nq-accent)] font-mono">
                    Cầu chì kênh gửi (Circuit Breakers)
                  </h3>

                  {/* Gmail Breaker */}
                  <div className="nq-surface-tile flex items-center justify-between p-3.5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">Kênh Gmail AI</span>
                        <StatusChip tone={breakers.gmail ? "danger" : "ok"}>
                          {breakers.gmail ? "ĐÃ NGẮT" : "Bình thường"}
                        </StatusChip>
                      </div>
                      <p className="mt-1 text-xs text-[var(--nq-dim)]">
                        {breakers.gmail
                          ? "Mọi lệnh gửi email tự động đang bị chặn trước transport."
                          : "Email được gửi bình thường theo quy trình kiểm duyệt."}
                      </p>
                    </div>
                    {owner ? (
                      <Btn
                        variant={breakers.gmail ? "primary" : "danger"}
                        onClick={() => toggleBreaker("gmail")}
                        busy={busy === "breaker:gmail"}
                        className="shrink-0 text-xs ml-3"
                      >
                        {breakers.gmail ? "Mở lại Gmail" : "Dừng Gmail AI"}
                      </Btn>
                    ) : null}
                  </div>

                  {/* Facebook Breaker */}
                  <div className="nq-surface-tile flex items-center justify-between p-3.5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">Kênh Fanpage Facebook</span>
                        <StatusChip tone={breakers.facebook ? "danger" : "ok"}>
                          {breakers.facebook ? "ĐÃ NGẮT" : "Bình thường"}
                        </StatusChip>
                      </div>
                      <p className="mt-1 text-xs text-[var(--nq-dim)]">
                        {breakers.facebook
                          ? "Mọi tin nhắn tự động đang bị chặn trước khi gửi đến Meta API."
                          : "Tin nhắn an toàn được tự động gửi cho khách hàng."}
                      </p>
                    </div>
                    {owner ? (
                      <Btn
                        variant={breakers.facebook ? "primary" : "danger"}
                        onClick={() => toggleBreaker("facebook")}
                        busy={busy === "breaker:facebook"}
                        className="shrink-0 text-xs ml-3"
                      >
                        {breakers.facebook ? "Mở lại Fanpage" : "Dừng Fanpage AI"}
                      </Btn>
                    ) : null}
                  </div>
                </div>

                {/* Flags list */}
                <div className="mt-6">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--nq-accent)] font-mono mb-2">
                    Cờ tính năng (Feature Flags)
                  </h3>
                  <div className="divide-y divide-[var(--nq-line)] border border-[var(--nq-line)] rounded-lg overflow-hidden bg-[var(--nq-surface-hi)]">
                    {Object.entries(operations?.flags ?? {}).map(([name, enabled]) => {
                      const meta = FLAG_META[name] ?? {
                        title: name.replace("NHIPQUAN_", ""),
                        desc: "Cờ cấu hình môi trường",
                      };
                      return (
                        <div key={name} className="flex items-center justify-between gap-3 p-3">
                          <div className="min-w-0 pr-2">
                            <p className="text-sm font-medium leading-tight">{meta.title}</p>
                            <p className="text-xs text-[var(--nq-dim)] font-mono truncate mt-0.5">
                              {name}
                            </p>
                          </div>
                          <StatusChip tone={enabled ? "ok" : "default"}>
                            {enabled ? "BẬT" : "TẮT"}
                          </StatusChip>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Retention & Dry Run */}
                <div className="mt-6 border-t border-[var(--nq-line)] pt-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">Lưu trữ & Dọn dẹp dữ liệu (Retention)</p>
                      <p className="text-xs text-[var(--nq-dim)]">
                        Thời gian lưu trữ: {operations?.retention_days ?? 180} ngày. Hệ thống chỉ hỗ trợ dry-run, không xóa tự động.
                      </p>
                    </div>
                    {owner ? (
                      <Btn
                        variant="ghost"
                        onClick={runDryRun}
                        busy={dryRunLoading}
                        className="text-xs"
                      >
                        Kiểm tra dọn dẹp (Dry Run)
                      </Btn>
                    ) : null}
                  </div>

                  {dryRunResult ? (
                    <div className="mt-3 rounded border border-[var(--nq-line)] bg-[var(--nq-bg)] p-3">
                      <p className="text-xs font-mono text-[var(--nq-accent)]">
                        Kết quả Dry-Run (dữ liệu &gt; {dryRunResult.retention_days} ngày đủ điều kiện dọn):
                      </p>
                      <ul className="mt-1.5 grid grid-cols-2 gap-2 text-xs font-mono">
                        <li>Bản sinh (Generations): {dryRunResult.eligible_counts.generation ?? 0}</li>
                        <li>Phản hồi (Feedbacks): {dryRunResult.eligible_counts.feedback ?? 0}</li>
                        <li>Đánh giá (Evaluations): {dryRunResult.eligible_counts.evaluation ?? 0}</li>
                        <li>Đề xuất quy tắc: {dryRunResult.eligible_counts.rule_proposal ?? 0}</li>
                      </ul>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}