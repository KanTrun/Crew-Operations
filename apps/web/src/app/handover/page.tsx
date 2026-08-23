"use client";

import { useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Field, PageHeader, textareaStyle } from "../../ui/kit";

export default function HandoverPage() {
  const [token, setToken] = useState("");
  const [text, setText] = useState(
    "Tình hình: hết đá\nBối cảnh: ca sáng đông\nĐánh giá: máy pha ổn\nĐề nghị: mua đá\nTreo: khăn ướt",
  );
  const [out, setOut] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getToken());
  }, []);

  async function run() {
    setError(null);
    try {
      const d = await apiSend<Record<string, unknown>>("/api/v1/handover", { text });
      setOut(d);
    } catch {
      setError("Không tách được bàn giao.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="SBAR"
        title="Bàn giao"
        meta="Tình hình · Bối cảnh · Đánh giá · Đề nghị. Claim đối lập → người duyệt."
      />
      <Field label="Nội dung ca">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} style={textareaStyle} />
      </Field>
      <Btn variant="primary" onClick={run}>
        Tách SBAR
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {out ? (
        <article className="nq-item nq-sop-answer">
          <p>
            <strong>Tình hình:</strong> {String(out.tinh_hinh ?? "—")}
          </p>
          <p>
            <strong>Bối cảnh:</strong> {String(out.boi_canh ?? "—")}
          </p>
          <p>
            <strong>Đánh giá:</strong> {String(out.danh_gia ?? "—")}
          </p>
          <p>
            <strong>Đề nghị:</strong> {String(out.de_nghi ?? "—")}
          </p>
        </article>
      ) : null}
    </div>
  );
}
