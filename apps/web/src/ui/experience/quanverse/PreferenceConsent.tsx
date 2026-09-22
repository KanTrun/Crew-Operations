"use client";

/**
 * PreferenceConsent — khách lưu sở thích, có đường xoá và có đồng thuận.
 *
 * Bản trước chỉ có một dòng input + nút, và thông báo "Cần khách đồng ý" hiện
 * ra sau khi đã gửi. Bản này cho thấy trước khi gửi: một ghi chú quyền riêng
 * tư nói rõ dữ liệu đi đâu, và sau khi gửi là một bước đồng thuận có nút riêng
 * — vì đây là dữ liệu cá nhân, không phải cài đặt giao diện.
 */

import { useState } from "react";
import { Icon } from "../../icons";

type Stage = "idle" | "awaiting_consent" | "saved";

export default function PreferenceConsent() {
  const [content, setContent] = useState("");
  const [proposal, setProposal] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  function authHeaders(json = false): Record<string, string> {
    return {
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...(tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {}),
    };
  }

  async function propose() {
    if (!content.trim()) return;
    setBusy(true);
    setNotice(null);
    setError(false);
    try {
      const res = await fetch(`${base}/api/v1/experience/quanverse/preferences/propose`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ content: content.trim() }),
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      const body = (await res.json()) as { preference_proposal_id: string; needs_consent: boolean };
      setProposal(body.preference_proposal_id);
      setStage(body.needs_consent ? "awaiting_consent" : "saved");
      setNotice(
        body.needs_consent
          ? "Đã ghi nhận. Cần bạn đồng ý trước khi lưu vào hồ sơ."
          : "Đã lưu vào hồ sơ của bạn.",
      );
      setContent("");
    } catch (e) {
      setError(true);
      setNotice(e instanceof Error ? e.message : "Không gửi được sở thích");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!proposal) return;
    setBusy(true);
    try {
      await fetch(`${base}/api/v1/experience/quanverse/preferences/${proposal}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      setNotice("Đã xoá sở thích — thao tác có lưu vết kiểm toán.");
      setProposal(null);
      setStage("idle");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="nq-pref" aria-label="Sở thích khách">
      <div className="nq-exp-section__head">
        <Icon name="pin" size={16} />
        <h3 className="nq-exp-section__title">Sở thích khách</h3>
        <span className="nq-exp-section__spacer" />
        <span className={`nq-stagechip nq-stagechip--${stage}`}>
          {stage === "saved" ? "Đã lưu" : stage === "awaiting_consent" ? "Chờ đồng ý" : "Chưa lưu"}
        </span>
      </div>

      <p className="nq-pref__privacy">
        <Icon name="info" size={14} />
        Sở thích là dữ liệu cá nhân: chỉ nhân viên phục vụ ca của bạn thấy, và bạn xoá được bất cứ lúc nào.
      </p>

      {stage !== "awaiting_consent" ? (
        <div className="nq-pref__row">
          <input
            type="text"
            value={content}
            data-testid="pref-input"
            placeholder="vd: thích bàn cửa sổ yên tĩnh"
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") propose();
            }}
          />
          <button
            type="button"
            className="nq-btn-compact nq-modebtn"
            data-testid="pref-propose"
            disabled={busy || !content.trim()}
            onClick={propose}
          >
            Đề xuất
          </button>
        </div>
      ) : (
        <div className="nq-consentbox">
          <p>
            Bạn muốn lưu sở thích này cho các lần ghé sau? Không đồng ý thì hệ thống quên ngay.
          </p>
          <div className="nq-consentbox__actions">
            <button
              type="button"
              className="nq-btn-compact nq-modebtn"
              data-testid="pref-delete"
              disabled={busy}
              onClick={remove}
            >
              <Icon name="trash" size={14} />
              Không đồng ý, xoá đi
            </button>
            <span className="nq-consentbox__hint">Mặc định: không lưu nếu bạn không bấm gì.</span>
          </div>
        </div>
      )}

      {proposal && stage === "saved" ? (
        <button
          type="button"
          className="nq-linkbtn"
          data-testid="pref-remove-saved"
          disabled={busy}
          onClick={remove}
        >
          <Icon name="trash" size={14} />
          Xoá sở thích đã lưu
        </button>
      ) : null}

      {notice ? (
        <p className={`nq-pref__notice${error ? " is-error" : ""}`} role={error ? "alert" : undefined}>
          {notice}
        </p>
      ) : null}
    </section>
  );
}