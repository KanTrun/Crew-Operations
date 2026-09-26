"use client";

import { FormEvent, useState } from "react";
import { apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { Btn, OpsCard } from "../kit";

type Turn = { question: string; answer: string; aiGenerated: boolean };

/**
 * Ô "Hỏi AI về trang này" — dùng cùng ngữ cảnh với `AiInsightPanel` nhưng cho
 * câu hỏi tự do, thay cho việc người quản lý phải tự đọc từng dòng dữ liệu để
 * suy ra câu trả lời.
 */
export function AskAiBox({ page }: { page: string }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiSend<{ ok: boolean; answer: string; ai_generated: boolean }>(
        "/api/v1/ai/insight/ask",
        { page, question: q },
      );
      setTurns((prev) => [...prev, { question: q, answer: res.answer, aiGenerated: res.ai_generated }]);
      setQuestion("");
    } catch (e) {
      setError(viError(e, { doing: "hỏi được AI về trang này" }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <OpsCard eyebrow="Hỏi thêm" title="Hỏi AI về trang này" density="compact">
      {turns.length > 0 ? (
        <div className="mb-3 space-y-3">
          {turns.map((t, i) => (
            <div key={i} className="space-y-1">
              <p className="text-sm font-semibold text-[var(--nq-fg)]">{t.question}</p>
              <p className="text-sm text-[var(--nq-ink-muted)]">{t.answer}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mb-3 text-sm text-[var(--nq-ink-muted)]">
          Ví dụ: “Vì sao mục đầu tiên có độ tin cậy thấp?”, “Tuần này có gì cần ưu tiên?”
        </p>
      )}
      {error ? <p className="mb-2 text-sm text-[var(--nq-st-danger-ink)]">{error}</p> : null}
      <form onSubmit={onSubmit} className="flex flex-wrap gap-2">
        <input
          className="nq-input min-w-0 flex-1"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Nhập câu hỏi…"
          disabled={busy}
        />
        <Btn type="submit" variant="primary" busy={busy} disabled={!question.trim()}>
          Hỏi
        </Btn>
      </form>
    </OpsCard>
  );
}
