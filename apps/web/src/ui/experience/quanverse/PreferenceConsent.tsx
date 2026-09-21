"use client";

/** PreferenceConsent — lưu sở thích khách cần consent, có delete path. */

import { useState } from "react";

export default function PreferenceConsent() {
  const [content, setContent] = useState("");
  const [proposal, setProposal] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  async function propose() {
    if (!content.trim()) return;
    setBusy(true);
    setNotice(null);
    try {
      const res = await fetch(`${base}/api/v1/experience/quanverse/preferences/propose`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {}),
        },
        body: JSON.stringify({ content: content.trim() }),
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      const body = (await res.json()) as { preference_proposal_id: string; needs_consent: boolean };
      setProposal(body.preference_proposal_id);
      setNotice(body.needs_consent ? "Cần khách đồng ý trước khi lưu." : "Đã lưu.");
      setContent("");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Lỗi");
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
        headers: tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {},
      });
      setNotice("Đã xoá sở thích (có audit).");
      setProposal(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="nq-pref" aria-label="Sở thích khách">
      <h3>Sở thích khách (consent)</h3>
      <div className="nq-pref__row">
        <input
          type="text"
          value={content}
          data-testid="pref-input"
          placeholder="vd: thích bàn cửa sổ yên tĩnh"
          onChange={(e) => setContent(e.target.value)}
        />
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          data-testid="pref-propose"
          disabled={busy || !content.trim()}
          onClick={propose}
        >
          Đề xuất
        </button>
        {proposal ? (
          <button type="button" className="nq-btn" data-testid="pref-delete" disabled={busy} onClick={remove}>
            Xoá
          </button>
        ) : null}
      </div>
      {notice ? <p className="nq-pref__notice">{notice}</p> : null}
    </section>
  );
}