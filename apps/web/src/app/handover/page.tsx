"use client";

import { useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Loading,
  OpsCard,
  PageHeader,
  textareaStyle,
} from "../../ui/kit";

type Sbar = { tinh_hinh?: unknown; boi_canh?: unknown; danh_gia?: unknown; de_nghi?: unknown };

export default function HandoverPage() {
  const [token, setToken] = useState("");
  const [text, setText] = useState(
    "Tình hình: hết đá\nBối cảnh: ca sáng đông\nĐánh giá: máy pha ổn\nĐề nghị: mua đá\nTreo: khăn ướt",
  );
  const [out, setOut] = useState<Sbar | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
  }, []);

  async function run() {
    setError(null);
    if (!text.trim()) {
      setError("Ghi nội dung ca trước khi tách bàn giao.");
      return;
    }
    setBusy(true);
    try {
      const d = await apiSend<Sbar>("/api/v1/handover", { text: text.trim() });
      setOut(d);
    } catch (e) {
      setError(viError(e, { doing: "tách được bàn giao thành bốn phần" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="SBAR"
        title="Bàn giao"
        meta="Ghi lại ca vừa rồi, hệ thống tách thành Tình hình · Bối cảnh · Đánh giá · Đề nghị cho ca sau."
      />
      <Field label="Nội dung ca">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} style={textareaStyle} />
      </Field>
      <Btn variant="primary" disabled={busy} onClick={run}>
        {busy ? "Đang tách…" : "Tách thành bàn giao"}
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {busy && !out ? <Loading skeleton="text">Đang tách nội dung ca…</Loading> : null}
      {out ? (
        <OpsCard eyebrow="Bàn giao cho ca sau" title="Bốn phần đã tách">
          <p>
            <strong>Tình hình:</strong> {safeText(out.tinh_hinh, "chưa nhận ra trong nội dung")}
          </p>
          <p>
            <strong>Bối cảnh:</strong> {safeText(out.boi_canh, "chưa nhận ra trong nội dung")}
          </p>
          <p>
            <strong>Đánh giá:</strong> {safeText(out.danh_gia, "chưa nhận ra trong nội dung")}
          </p>
          <p>
            <strong>Đề nghị:</strong> {safeText(out.de_nghi, "chưa nhận ra trong nội dung")}
          </p>
        </OpsCard>
      ) : (
        !busy && !error && <Empty>Chưa tách lần nào. Ghi nội dung ca rồi bấm tách.</Empty>
      )}
    </div>
  );
}
