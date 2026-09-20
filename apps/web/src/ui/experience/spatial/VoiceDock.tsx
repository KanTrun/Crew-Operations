"use client";

/** VoiceDock — voice/text input + response grounded + replay control. */

import { useEffect, useRef, useState } from "react";

interface VoiceResponse {
  turn_id: string;
  transcript: string;
  response_text: string;
  citations: string[];
  grounded: boolean;
  proposal?: { proposal_id: string } | null;
}

interface Props {
  anchorId: string | null;
}

export default function VoiceDock({ anchorId }: Props) {
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState<VoiceResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  async function ask() {
    const text = transcript.trim();
    if (!text) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${base}/api/v1/experience/voice/turn`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {}),
        },
        body: JSON.stringify({
          conversation_id: `conv_${Date.now()}`,
          transcript: text,
          anchor_id: anchorId,
          requester_id: "quan_ly_demo",
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as { detail?: string }).detail || `api_${res.status}`);
      }
      setResponse((await res.json()) as VoiceResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi voice");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <section className="nq-voicedock" aria-label="Giọng nói / văn bản HỒN QUÁN">
      <div className="nq-voicedock__input">
        <input
          ref={inputRef}
          type="text"
          value={transcript}
          data-testid="voice-input"
          onChange={(e) => setTranscript(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Hỏi: 'Ở đây từng xảy ra chuyện gì?' hoặc 'Nhớ điều này…'"
          aria-label="Hỏi HỒN QUÁN"
        />
        <button
          type="button"
          className="nq-btn nq-btn--primary"
          data-testid="voice-ask"
          disabled={busy || !transcript.trim()}
          onClick={ask}
        >
          {busy ? "Đang xử lý…" : "Hỏi"}
        </button>
      </div>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}

      {response ? (
        <div className="nq-voicedock__response" data-testid="voice-response" aria-live="polite">
          <p className="nq-voicedock__text">{response.response_text}</p>
          {response.citations.length ? (
            <p className="nq-voicedock__citations">
              Nguồn: {response.citations.join(", ")}
            </p>
          ) : null}
          {response.proposal ? (
            <p className="nq-voicedock__proposal">
              Đề xuất ký ức {response.proposal.proposal_id} — chờ xác nhận.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}