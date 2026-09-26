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
  // Hiện cảnh báo đỏ khi còn ít hơn 10 phút
  const isUrgent = isPending && timeLeft && (() => {
    const parts = timeLeft.split(":");
    const minutes = parseInt(parts[0] ?? "999", 10);
    return minutes < 10;
  })();

  return (
    <div className={`mt-3 p-3.5 rounded-xl border text-xs text-zinc-200 ${
      isUrgent
        ? "border-rose-500/40 bg-rose-500/5"
        : "border-amber-500/30 bg-amber-500/5"
    }`}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="font-semibold text-[var(--nq-st-warn-ink)] flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-[var(--nq-st-warn)] animate-pulse"></span>
          Đề xuất: {proposal.intent}
        </span>
        <div className="flex items-center gap-2">
          {timeLeft && isPending && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
              isUrgent
                ? "bg-rose-900/60 text-rose-300 border border-rose-500/40"
                : "bg-zinc-800 text-zinc-400"
            }`}>
              {isUrgent ? "⚠️" : "⏳"} {timeLeft}
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
      {/* Hint text: hướng dẫn duyệt qua chat */}
      {isPending && (
        <p className={`text-[10px] mb-2 ${isUrgent ? "text-rose-400" : "text-zinc-500"}`}>
          {isUrgent
            ? `⚠️ Còn ${timeLeft} — nhắn "Duyệt" hoặc bấm nút bên dưới trước khi hết hạn!`
            : `💬 Nhắn "Duyệt" hoặc bấm nút bên dưới để xác nhận`}
        </p>
      )}

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

      {/* Chi tiết payload_diff cho MỌI intent (trừ SEND_MAIL đã có hiển thị riêng).
          Giúp người duyệt thấy nội dung THẬT sẽ được ghi, không chỉ bản tóm tắt. */}
      {proposal.intent !== "SEND_MAIL" && proposal.payload_diff && (
        <PayloadDetail payload={proposal.payload_diff} intent={proposal.intent} />
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

// ── Hiển thị chi tiết payload_diff cho mọi intent ───────────────────────────
// Mục đích: người duyệt thấy nội dung THẬT sẽ được ghi vào hệ thống (không chỉ
// bản tóm tắt summary/explanation), để tránh duyệt nhầm khi AI hiểu sai ý.

const PAYLOAD_LABELS: Record<string, string> = {
  // Chung
  snapshot_version: "Phiên bản dữ liệu",
  // Xếp lịch
  tuan: "Tuần",
  tuan_iso: "Tuần (ISO)",
  status: "Trạng thái",
  phan_cong: "Phân công ca",
  uu_tien: "Ưu tiên nhân sự",
  meeting_adjustments: "Điều chỉnh từ cuộc họp",
  rules_applied: "Luật đã áp dụng",
  // Đổi ca
  swap_id: "Mã lượt đổi ca",
  ca_id: "Mã ca",
  tu_nv: "Nhân viên nhả ca",
  nhan_nv: "Nhân viên nhận ca",
  trung_gian: "Nhân viên trung gian",
  dong_y: "Đã đồng ý",
  kiem_tra_5_dieu_kien: "Kiểm tra 5 điều kiện",
  thoa_man_5_dieu_kien: "Thỏa mãn 5 điều kiện",
  // Việc treo / bàn giao
  noi_dung: "Nội dung",
  treo_id: "Mã việc treo",
  nv_id: "Nhân viên",
  text: "Nội dung bàn giao",
  // Tiêu thụ
  hang: "Mặt hàng",
  so_luong: "Số lượng",
  don_vi: "Đơn vị",
  // Menu
  hanh_dong: "Hành động",
  ten_mon: "Tên món",
  mon_id: "Mã món",
  gia: "Giá mới",
  gia_cu: "Giá cũ",
  an: "Ẩn món",
  // Đơn quầy
  don_id: "Mã đơn",
  trang_thai: "Trạng thái đích",
  trang_thai_hien_tai: "Trạng thái hiện tại",
  ly_do_huy: "Lý do hủy",
  // Ghim ca
  pinned: "Ghim",
  // TKB
  khoang_ban: "Khoảng bận",
  source_id: "Nguồn",
  upload_id: "Mã tệp tải lên",
  // Xin nghỉ
  thu: "Thứ",
  ly_do: "Lý do",
  // Khảo sát giá
  category_keyword: "Ngành hàng",
  radius_km: "Bán kính (km)",
  channel_mode: "Kênh khảo sát",
  include_substitutes: "Bao gồm sản phẩm thay thế",
  quota_cost: "Chi phí hạn ngạch",
  quota_remaining: "Hạn ngạch còn lại",
  quota_warning: "Cảnh báo hạn ngạch",
  requested_by: "Người yêu cầu",
  requested_role: "Vai trò yêu cầu",
  // Fanpage
  topic: "Chủ đề",
  tone: "Giọng văn",
  so_ky_tu: "Số ký tự",
  // Luật
  de_xuat: "Đề xuất luật",
  so_lan_sua: "Số lần sửa",
  so_mau: "Số mẫu lặp",
  co_de_xuat: "Có đề xuất",
};

// Các trường nội bộ không cần hiển thị cho người duyệt.
const PAYLOAD_HIDDEN = new Set([
  "snapshot_version",
  "co_du_lieu",
  "co_de_xuat",
  "quota_warning",
]);

function formatValue(value: any): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function PayloadDetail({ payload, intent }: { payload: Record<string, any>; intent: string }) {
  const entries = Object.entries(payload).filter(
    ([key, value]) =>
      !PAYLOAD_HIDDEN.has(key) &&
      value !== null &&
      value !== undefined &&
      !(typeof value === "object" && Object.keys(value).length === 0)
  );

  if (entries.length === 0) return null;

  return (
    <div className="my-2 p-3 rounded-lg bg-zinc-950/70 border border-zinc-800 text-xs font-sans">
      <div className="flex items-center gap-1.5 pb-1.5 mb-1.5 border-b border-zinc-800/60 text-zinc-400 text-[10px] font-medium">
        <span>📋</span>
        <span>Chi tiết nội dung sẽ được áp dụng ({intent})</span>
      </div>
      <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
        {entries.map(([key, value]) => {
          const label = PAYLOAD_LABELS[key] || key;
          const isObject = typeof value === "object" && value !== null;
          return (
            <div key={key} className="flex items-start gap-2">
              <span className="text-zinc-500 font-semibold min-w-[110px] shrink-0">{label}:</span>
              <span className={`text-zinc-200 break-words ${isObject ? "font-mono text-[10px] whitespace-pre-wrap" : ""}`}>
                {formatValue(value)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
