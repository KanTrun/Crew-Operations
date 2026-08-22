"use client";

import { useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnPrimary, Field, inputStyle, Kicker } from "../../ui/kit";

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
    <div className="nq-page">
      <Kicker>SBAR</Kicker>
      <h1>Bàn giao</h1>
      <p className="nq-muted">Tình hình · Bối cảnh · Đánh giá · Đề nghị. Nếu có claim đối lập, hệ thống đưa người duyệt.</p>
      <Field label="Nội dung ca">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} style={inputStyle} />
      </Field>
      <button onClick={run} style={btnPrimary}>
        Tách SBAR
      </button>
      {error ? <Alert>{error}</Alert> : null}
      {out ? (
        <article className="nq-item" style={{ marginTop: "1rem" }}>
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
