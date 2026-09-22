"use client";

/**
 * VoiceDock — hỏi HỒN QUÁN bằng chữ (mic là bước sau), trả lời có căn cứ.
 *
 * Không in `proposal_id` ra UI: người hỏi cần biết "đã đề xuất ghi nhớ" và
 * "đang chờ ai duyệt", không cần mã nội bộ.
 */

import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../../lib/api";
import { viError } from "../../../lib/present";
import { Icon } from "../../icons";

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

const COPY = {
  ask: {
    doing: "hỏi được HỒN QUÁN",
    missing: "Neo này chưa có ký ức nào để trả lời. Chọn neo khác hoặc ghi nhớ điều gì đó trước.",
  },
} as const;

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
      if (!res.ok) throw new ApiError(res.status);
      setResponse((await res.json()) as VoiceResponse);
    } catch (e) {
      setError(viError(e, COPY.ask));
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
          className="nq-btn nq-btn-primary"
          data-testid="voice-ask"
          disabled={busy || !transcript.trim() || !anchorId}
          onClick={ask}
        >
          <Icon name="send" size={15} />
          {busy ? "Đang xử lý…" : "Hỏi"}
        </button>
      </div>

      {!anchorId ? (
        <p className="nq-voicedock__hint">
          Chọn một neo trên bản đồ trước — câu trả lời luôn gắn với một khu vực cụ thể.
        </p>
      ) : null}

      {error ? (
        <div className="nq-alert nq-alert--error" role="alert">
          {error}
        </div>
      ) : null}

      {response ? (
        <div className="nq-voicedock__response" data-testid="voice-response" aria-live="polite">
          <p className="nq-voicedock__text">{response.response_text}</p>
          <p className="nq-voicedock__citations">
            {response.citations.length
              ? `Dựa trên ${response.citations.length} ký ức đã xác nhận`
              : "Chưa có ký ức nào đã xác nhận ở khu vực này"}
          </p>
          {response.proposal ? (
            <p className="nq-voicedock__proposal">
              <Icon name="pin" size={13} />
              Đã đề xuất ghi nhớ điều này — chờ quản lý xác nhận trước khi lưu.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}