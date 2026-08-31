"use client";

import React, { useState, useEffect } from "react";
import { getToken } from "../../lib/session";

export interface ActionProposalData {
  action_id: string;
  intent: string;
  status: "draft" | "ready_for_approval" | "executed" | "rejected" | "expired" | "stale_rejected";
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
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [amendReason, setAmendReason] = useState("");

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
    try {
      const res = await fetch("http://localhost:8000/api/v1/copilot/execute-action", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          action_id: proposal.action_id,
          decision,
          idempotency_key: `key_${Date.now()}`,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Không thể thực thi hành động.");
      }

      setCurrentStatus(data.status);
      if (onExecuted) {
        onExecuted({ ...proposal, status: data.status, executed_at: new Date().toISOString() });
      }
    } catch (err: any) {
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
      const res = await fetch(`http://localhost:8000/api/v1/copilot/action/${proposal.action_id}/amend`, {
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

  const isPending = currentStatus === "draft" || currentStatus === "ready_for_approval";

  return (
    <div className="mt-3 p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/5 text-xs text-zinc-200">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="font-semibold text-amber-400 flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          Đề xuất: {proposal.intent}
        </span>
        <div className="flex items-center gap-2">
          {timeLeft && isPending && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
              ⏳ {timeLeft}
            </span>
          )}
          <span
            className={`text-[10px] font-medium px-2 py-0.5 rounded ${
              currentStatus === "executed"
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : currentStatus === "rejected" || currentStatus === "stale_rejected" || currentStatus === "expired"
                ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
            }`}
          >
            {currentStatus === "executed"
              ? "✓ ĐÃ DUYỆT"
              : currentStatus === "rejected"
              ? "✕ ĐÃ TỪ CHỐI"
              : currentStatus === "stale_rejected"
              ? "⚠️ DỮ LIỆU CŨ"
              : currentStatus === "expired"
              ? "⏳ HẾT HẠN"
              : "CHỜ DUYỆT"}
          </span>
        </div>
      </div>

      <p className="text-zinc-100 font-medium mb-1">{proposal.summary}</p>
      {proposal.explanation && (
        <p className="text-zinc-400 text-[11px] mb-2 leading-relaxed italic">
          {proposal.explanation}
        </p>
      )}

      {errorMsg && (
        <div className="mb-2 p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[11px]">
          {errorMsg}
        </div>
      )}

      {isPending && (
        <div className="flex items-center gap-2 pt-2 border-t border-zinc-800">
          <button
            onClick={() => handleDecision("approve")}
            disabled={loading}
            className="flex-1 py-1.5 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-white transition disabled:opacity-50"
          >
            {loading ? "Đang xử lý..." : "✓ Duyệt & Áp dụng"}
          </button>
          <button
            onClick={() => handleDecision("reject")}
            disabled={loading}
            className="py-1.5 px-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition disabled:opacity-50"
          >
            ✕ Từ chối
          </button>
        </div>
      )}

      {currentStatus === "executed" && (
        <div className="pt-2 border-t border-zinc-800 flex justify-end">
          <button
            onClick={() => setShowAmendModal(true)}
            className="text-[11px] text-zinc-400 hover:text-amber-400 underline"
          >
            Đính chính / Sửa lại
          </button>
        </div>
      )}

      {/* Amend Modal */}
      {showAmendModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-4 max-w-sm w-full">
            <h4 className="text-sm font-semibold text-zinc-100 mb-2">Đính chính hành động</h4>
            <textarea
              value={amendReason}
              onChange={(e) => setAmendReason(e.target.value)}
              placeholder="Nhập lý do đính chính (vd: Nhân viên đổi ý, sửa lại ca...)"
              className="w-full h-20 p-2 text-xs bg-zinc-800 border border-zinc-700 rounded text-zinc-100 mb-3 focus:outline-none focus:border-amber-500"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowAmendModal(false)}
                className="px-3 py-1 text-xs rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              >
                Hủy
              </button>
              <button
                onClick={handleAmend}
                disabled={loading || !amendReason.trim()}
                className="px-3 py-1 text-xs rounded bg-amber-600 hover:bg-amber-500 text-white font-medium disabled:opacity-50"
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
