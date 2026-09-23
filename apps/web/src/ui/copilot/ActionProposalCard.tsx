"use client";

import React, { useState, useEffect, useRef } from "react";
import { getToken } from "../../lib/session";
import { ChatText } from "./ChatText";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ActionProposalData {
  action_id: string;
  intent: string;
  status: "draft" | "ready_for_approval" | "amendment_ready" | "executing" | "executed" | "execution_failed" | "rejected" | "expired" | "stale_rejected";
  summary: string;
  explanation: string;
  payload_diff: Record<string, any>;
  requires_confirmation: boolean;
  store_id: string;
  created_by: string;
  confidence: number;
  data_snapshot_hash: string;
  expires_at: string;
  created_at?: string;
  executed_at?: string | null;
  amended_from?: string | null;
}

interface ActionProposalCardProps {
  proposal: ActionProposalData;
  onExecuted?: (updated: ActionProposalData) => void;
}

export function ActionProposalCard({ proposal, onExecuted }: ActionProposalCardProps) {
  const [currentStatus, setCurrentStatus] = useState(proposal.status);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [resultLink, setResultLink] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [amendReason, setAmendReason] = useState("");

  // Email inline editing & personalization
  const [isEditingEmail, setIsEditingEmail] = useState(false);
  const [editSubject, setEditSubject] = useState(proposal.payload_diff?.subject || "");
  const [editBody, setEditBody] = useState(proposal.payload_diff?.body || "");
  const decisionKey = useRef(`approve_${proposal.action_id}_${crypto.randomUUID()}`);

  useEffect(() => {
    setEditSubject(proposal.payload_diff?.subject || "");
    setEditBody(proposal.payload_diff?.body || "");
    setCurrentStatus(proposal.status);
  }, [proposal]);

  useEffect(() => {
    if (!proposal.expires_at || currentStatus === "executed" || currentStatus === "rejected") {
      setTimeLeft("");
      return;
    }

    const interval = setInterval(() => {
      const exp = new Date(proposal.expires_at).getTime();
      const now = new Date().getTime();
      const diff = Math.max(0, Math.floor((exp - now) / 1000));
      if (diff <= 0) {
        setTimeLeft("Đã hết hạn");
        setCurrentStatus("expired");
        clearInterval(interval);
      } else {
        const m = Math.floor(diff / 60);
        const s = diff % 60;
        setTimeLeft(`${m}:${s < 10 ? "0" : ""}${s}`);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [proposal.expires_at, currentStatus]);

  async function handleDecision(decision: "approve" | "reject") {
    setLoading(true);
    setErrorMsg(null);
    if (decision === "approve") {
      setCurrentStatus("executing");
    }
    try {
      let correctionDiff: Record<string, any> | undefined = undefined;
      if (
        proposal.intent === "SEND_MAIL" &&
        decision === "approve" &&
        (editSubject !== proposal.payload_diff?.subject || editBody !== proposal.payload_diff?.body)
      ) {
        correctionDiff = {
          subject: editSubject,
          body: editBody,
        };
      }

      const res = await fetch(`${API_BASE}/api/v1/copilot/execute-action`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          action_id: proposal.action_id,
          decision,
          idempotency_key: decision === "approve" ? decisionKey.current : `reject_${crypto.randomUUID()}`,
          correction_diff: correctionDiff,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = String(data.detail || "");
        if (detail.includes("stale_rejected")) {
          setCurrentStatus("stale_rejected");
        } else if (detail.includes("expired")) {
          setCurrentStatus("expired");
        } else if (detail.includes("execution_failed") || res.status >= 500) {
          setCurrentStatus("execution_failed");
        } else if (detail.includes("invalid_action_status:executing")) {
          setCurrentStatus("executing");
        } else {
          setCurrentStatus(proposal.status);
        }
        throw new Error(detail || "Không thể thực thi hành động.");
      }
      setCurrentStatus(data.status);
      setResultLink(data.result_link ?? null);
      if (onExecuted) {
        onExecuted({ ...proposal, status: data.status, executed_at: new Date().toISOString() });
      }
    } catch (err: any) {
      if (currentStatus === "executing") {
        setCurrentStatus("execution_failed");
      }
      setErrorMsg(err.message || "Lỗi kết nối.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAmend() {
    if (!amendReason.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/copilot/action/${proposal.action_id}/amend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          reason: amendReason,
          correction_diff: proposal.payload_diff,
          idempotency_key: `amend_${Date.now()}`,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Không thể gửi đính chính.");
      }

      setShowAmendModal(false);
      setAmendReason("");
      alert(`Đã tạo bản ghi đính chính: ${data.new_action_id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Lỗi kết nối.");
    } finally {
      setLoading(false);
    }
  }

  const isPending = currentStatus === "draft" || currentStatus === "ready_for_approval" || currentStatus === "amendment_ready";

  return (
    <div className="mt-3 p-3.5 rounded-xl border border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))] bg-[var(--nq-st-warn-soft)] text-xs text-[var(--nq-ink)]">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="font-semibold text-[var(--nq-st-warn-ink)] flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-[var(--nq-st-warn)] animate-pulse"></span>
          Đề xuất: {proposal.intent}
        </span>
        <div className="flex items-center gap-2">
          {timeLeft && isPending && (
            <span className="text-2xs px-1.5 py-0.5 rounded bg-[var(--nq-surface)] text-[var(--nq-ink-muted)]">
              ⏳ {timeLeft}
            </span>
          )}
          <span
            className={`text-2xs font-medium px-2 py-0.5 rounded ${
              currentStatus === "executed"
                ? "bg-[var(--nq-st-ok-soft)] text-[var(--nq-st-ok-ink)] border border-[color-mix(in_srgb,var(--nq-st-ok)_46%,var(--nq-line))]"
                : currentStatus === "rejected" || currentStatus === "execution_failed" || currentStatus === "stale_rejected" || currentStatus === "expired"
                ? "bg-[var(--nq-st-danger-soft)] text-[var(--nq-st-danger-ink)] border border-[color-mix(in_srgb,var(--nq-st-danger)_46%,var(--nq-line))]"
                : "bg-[var(--nq-st-warn-soft)] text-[var(--nq-st-warn-ink)] border border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))]"
            }`}
          >
            {currentStatus === "executed"
              ? "✓ ĐÃ DUYỆT"
              : currentStatus === "executing"
              ? "ĐANG THỰC THI"
              : currentStatus === "execution_failed"
              ? "THỰC THI THẤT BẠI"
              : currentStatus === "rejected"
              ? "✕ ĐÃ TỪ CHỐI"
              : currentStatus === "stale_rejected"
              ? "⚠️ DỮ LIỆU CŨ"
              : currentStatus === "expired"
              ? "⏳ HẾT HẠN"
              : currentStatus === "amendment_ready"
              ? "CHỜ DUYỆT ĐÍNH CHÍNH"
              : "CHỜ DUYỆT"}
          </span>
        </div>
      </div>

      <p className="text-[var(--nq-ink)] font-medium mb-1">
        <ChatText text={proposal.summary} />
      </p>
      {proposal.explanation && (
        <p className="text-[var(--nq-ink-muted)] text-2xs mb-2 leading-relaxed italic">
          <ChatText text={proposal.explanation} />
        </p>
      )}

      {proposal.intent === "SEND_MAIL" && proposal.payload_diff && (
        <div className="my-2 p-3 rounded-lg bg-[var(--nq-bg)] border border-[var(--nq-line)] text-xs font-sans space-y-2.5">
          {/* Metadata Badges: Live Context & Learned Style */}
          <div className="flex flex-wrap items-center gap-1.5 pb-1 border-b border-[var(--nq-line)]">
            {proposal.payload_diff.ops_context_summary && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--nq-st-info-soft)] border border-[color-mix(in_srgb,var(--nq-st-info)_46%,var(--nq-line))] text-[var(--nq-st-info-ink)] text-2xs font-medium">
                <span>⚡ Dữ liệu sống:</span>
                <span>{proposal.payload_diff.ops_context_summary}</span>
              </span>
            )}
            {proposal.payload_diff.has_learned_style && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--nq-st-info-soft)] border border-[color-mix(in_srgb,var(--nq-st-info)_46%,var(--nq-line))] text-[var(--nq-st-info-ink)] text-2xs font-medium">
                <span>✨ Đã áp dụng văn phong ưa thích</span>
              </span>
            )}
            {isPending && !isEditingEmail && (
              <button
                type="button"
                onClick={() => setIsEditingEmail(true)}
                className="ml-auto text-2xs text-[var(--nq-st-warn-ink)] hover:text-[var(--nq-st-warn-ink)] underline flex items-center gap-0.5"
              >
                ✏️ Sửa trước khi duyệt
              </button>
            )}
            {isPending && isEditingEmail && (
              <button
                type="button"
                onClick={() => setIsEditingEmail(false)}
                className="ml-auto text-2xs text-[var(--nq-ink-muted)] hover:text-[var(--nq-ink)] underline flex items-center gap-0.5"
              >
                Thu gọn chỉnh sửa
              </button>
            )}
          </div>

          <div className="flex items-start gap-1.5 text-[var(--nq-ink)]">
            <span className="text-[var(--nq-ink-muted)] font-semibold min-w-[70px]">Người nhận:</span>
            <span className="text-[var(--nq-st-warn-ink)] font-mono">
              {Array.isArray(proposal.payload_diff.to_emails) && proposal.payload_diff.to_emails.length > 0
                ? proposal.payload_diff.to_emails.join(", ")
                : proposal.payload_diff.recip_label || "Chưa có email"}
            </span>
          </div>

          <div className="flex items-start gap-1.5 text-[var(--nq-ink)]">
            <span className="text-[var(--nq-ink-muted)] font-semibold min-w-[70px]">Tiêu đề:</span>
            {isEditingEmail ? (
              <input
                type="text"
                value={editSubject}
                onChange={(e) => setEditSubject(e.target.value)}
                className="flex-1 bg-[var(--nq-bg-elevated)] border border-[var(--nq-line)] rounded px-2 py-1 text-[var(--nq-ink)] text-xs focus:outline-none focus:border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))]"
              />
            ) : (
              <span className="text-[var(--nq-ink)] font-medium">
                {editSubject || proposal.payload_diff.subject || "(Chưa có tiêu đề)"}
              </span>
            )}
          </div>

          <div className="pt-2 border-t border-[var(--nq-line)]">
            <span className="text-[var(--nq-ink-muted)] font-semibold block mb-1">Nội dung thư:</span>
            {isEditingEmail ? (
              <textarea
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                rows={7}
                className="w-full bg-[var(--nq-bg-elevated)] border border-[var(--nq-line)] rounded p-2.5 text-[var(--nq-ink)] text-2xs leading-relaxed focus:outline-none focus:border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))] font-sans"
              />
            ) : (
              <div className="bg-[var(--nq-bg-elevated)] rounded p-2.5 text-[var(--nq-ink)] text-2xs leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto font-sans border border-[var(--nq-line)]">
                {editBody || proposal.payload_diff.body || "(Trống)"}
              </div>
            )}
          </div>

          {Array.isArray(proposal.payload_diff.attachments) && proposal.payload_diff.attachments.length > 0 && (
            <div className="pt-2 border-t border-[var(--nq-line)]">
              <span className="text-[var(--nq-ink-muted)] font-semibold block mb-1.5 flex items-center gap-1 text-2xs">
                <span>📎</span> Tệp & hình ảnh đính kèm ({proposal.payload_diff.attachments.length}):
              </span>
              <div className="flex flex-wrap gap-2">
                {proposal.payload_diff.attachments.map((att: any, idx: number) => {
                  const fname = typeof att === "string" ? att.split(/[/\\]/).pop() : (att.filename || "file");
                  const isInline = typeof att === "object" && (att.is_inline || att.cid);
                  return (
                    <div
                      key={idx}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--nq-bg-elevated)] border border-[var(--nq-line)] text-2xs text-[var(--nq-ink)]"
                    >
                      <span className="text-[var(--nq-st-warn-ink)]">🖼️</span>
                      <span className="font-mono">{fname}</span>
                      {isInline && (
                        <span className="text-2xs bg-[var(--nq-st-info-soft)] text-[var(--nq-st-info-ink)] px-1 py-0.5 rounded border border-[color-mix(in_srgb,var(--nq-st-info)_46%,var(--nq-line))]">
                          Chèn trong thư
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {errorMsg && (
        <div className="mb-2 p-2 rounded bg-[var(--nq-st-danger-soft)] border border-[color-mix(in_srgb,var(--nq-st-danger)_46%,var(--nq-line))] text-[var(--nq-st-danger-ink)] text-2xs">
          {errorMsg}
          {currentStatus === "stale_rejected" && " Hãy tạo đề xuất mới từ dữ liệu hiện tại."}
          {currentStatus === "expired" && " Hãy tạo đề xuất mới để tiếp tục."}
          {currentStatus === "execution_failed" && " Kiểm tra trạng thái hành động trước khi thử lại."}
        </div>
      )}

      {isPending && (
        <div className="flex items-center gap-2 pt-2 border-t border-[var(--nq-line)]">
          <button
            onClick={() => handleDecision("approve")}
            disabled={loading}
            className="flex-1 py-1.5 px-3 rounded-lg bg-[var(--nq-st-ok)] hover:bg-[var(--nq-st-ok)] font-semibold text-[var(--nq-accent-ink)] transition disabled:opacity-50"
          >
            {loading
              ? "Đang gửi..."
              : proposal.intent === "SEND_MAIL"
              ? "✓ Duyệt & Gửi email"
              : "✓ Duyệt & Áp dụng"}
          </button>
          <button
            onClick={() => handleDecision("reject")}
            disabled={loading}
            className="py-1.5 px-3 rounded-lg bg-[var(--nq-surface)] hover:bg-[var(--nq-line)] text-[var(--nq-ink)] transition disabled:opacity-50"
          >
            ✕ Từ chối
          </button>
        </div>
      )}
      {currentStatus === "executed" && (
        <div className="pt-2 border-t border-[var(--nq-line)] flex items-center justify-between gap-2">
          {resultLink ? (
            <a
              href={resultLink}
              className="inline-flex items-center gap-1 text-2xs px-2 py-1 rounded bg-[var(--nq-st-ok-soft)] text-[var(--nq-st-ok-ink)] border border-[color-mix(in_srgb,var(--nq-st-ok)_46%,var(--nq-line))] hover:bg-[var(--nq-st-ok-soft)] transition"
            >
              → Xem kết quả đã áp dụng
            </a>
          ) : (
            <span />
          )}
          <button
            onClick={() => setShowAmendModal(true)}
            className="text-2xs text-[var(--nq-ink-muted)] hover:text-[var(--nq-st-warn-ink)] underline"
          >
            Đính chính / Sửa lại
          </button>
        </div>
      )}

      {/* Amend Modal */}
      {showAmendModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--nq-bg-elevated)] border border-[var(--nq-line)] rounded-xl p-4 max-w-sm w-full">
            <h4 className="text-sm font-semibold text-[var(--nq-ink)] mb-2">Đính chính hành động</h4>
            <textarea
              value={amendReason}
              onChange={(e) => setAmendReason(e.target.value)}
              placeholder="Nhập lý do đính chính (vd: Nhân viên đổi ý, sửa lại ca...)"
              className="w-full h-20 p-2 text-xs bg-[var(--nq-surface)] border border-[var(--nq-line)] rounded text-[var(--nq-ink)] mb-3 focus:outline-none focus:border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))]"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowAmendModal(false)}
                className="px-3 py-1 text-xs rounded bg-[var(--nq-surface)] text-[var(--nq-ink)] hover:bg-[var(--nq-line)]"
              >
                Hủy
              </button>
              <button
                onClick={handleAmend}
                disabled={loading || !amendReason.trim()}
                className="px-3 py-1 text-xs rounded bg-[var(--nq-st-warn)] hover:bg-[var(--nq-st-warn)] text-[var(--nq-accent-ink)] font-medium disabled:opacity-50"
              >
                Gửi đính chính
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
